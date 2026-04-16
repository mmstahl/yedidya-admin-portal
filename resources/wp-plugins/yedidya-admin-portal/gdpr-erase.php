<?php
/**
 * GDPR user erasure — REST endpoint.
 * Loaded by yedidya-admin-portal.php.
 *
 * ENDPOINT
 *   POST /wp-json/yedidya/v1/gdpr-erase
 *   Body (JSON): { "email": "user@example.com" }
 *   Auth: WordPress application password with delete_users capability
 *
 * RESPONSE (JSON)
 *   { "success": true, "email": "...", "steps": [...], "warnings": [...] }
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

add_action( 'rest_api_init', function () {
    register_rest_route( 'yedidya/v1', '/gdpr-erase', [
        'methods'             => 'POST',
        'callback'            => 'yedidya_gdpr_erase_handler',
        'permission_callback' => function () {
            return current_user_can( 'delete_users' );
        },
        'args' => [
            'email' => [
                'required'          => true,
                'type'              => 'string',
                'sanitize_callback' => 'sanitize_email',
                'validate_callback' => function ( $value ) {
                    return is_email( $value );
                },
            ],
        ],
    ] );
} );

if ( ! function_exists( 'yedidya_gdpr_erase_handler' ) ) {
    function yedidya_gdpr_erase_handler( WP_REST_Request $request ) {
        $email    = $request->get_param( 'email' );
        $warnings = [];
        $steps    = [];

        // ── 1. WooCommerce: delete orders ──────────────────────────────────────
        if ( function_exists( 'wc_get_orders' ) ) {

            $orders = wc_get_orders( [
                'customer' => $email,
                'limit'    => -1,
                'status'   => 'any',
            ] );

            $order_count = count( $orders );
            foreach ( $orders as $order ) {
                $order->delete( true ); // force-delete, skip trash
            }
            $steps[] = "WooCommerce: deleted {$order_count} order(s).";

            // Remove row from customer lookup table
            global $wpdb;
            $rows_deleted = $wpdb->delete(
                $wpdb->prefix . 'wc_customer_lookup',
                [ 'email' => $email ],
                [ '%s' ]
            );
            $steps[] = "WooCommerce: removed customer lookup record ({$rows_deleted} row(s)).";

        } else {
            $warnings[] = "WooCommerce is not active — WC data was not erased.";
        }

        // ── 2. WooCommerce: delete session ─────────────────────────────────────
        if ( class_exists( 'WC_Session_Handler' ) ) {
            $user = get_user_by( 'email', $email );
            if ( $user ) {
                $session_handler = new WC_Session_Handler();
                $session_handler->delete_session( $user->ID );
                $steps[] = "WooCommerce: deleted active session.";
            }
        }

        // ── 3. Run all registered WordPress privacy erasers ────────────────────
        $erasers = apply_filters( 'wp_privacy_personal_data_erasers', [] );
        foreach ( $erasers as $eraser_key => $eraser ) {
            if ( ! isset( $eraser['callback'] ) ) {
                continue;
            }
            try {
                call_user_func( $eraser['callback'], $email, 1 );
            } catch ( Exception $e ) {
                $warnings[] = "Eraser '{$eraser_key}' failed: " . $e->getMessage();
            }
        }
        $steps[] = "Ran all registered WordPress privacy erasers (" . count( $erasers ) . " eraser(s)).";

        // ── 4. Delete WordPress user account + all their content ───────────────
        $user = get_user_by( 'email', $email );
        if ( $user ) {
            require_once ABSPATH . 'wp-admin/includes/user.php';
            $deleted = wp_delete_user( $user->ID, null );
            if ( $deleted ) {
                $steps[] = "WordPress: user account and all content deleted.";
            } else {
                $warnings[] = "WordPress: wp_delete_user() returned false — account may not be fully deleted.";
            }
        } else {
            $steps[] = "WordPress: no account found for this email (already deleted, or never existed) — skipped.";
        }

        return rest_ensure_response( [
            'success'  => true,
            'email'    => $email,
            'steps'    => $steps,
            'warnings' => $warnings,
        ] );
    }
}
