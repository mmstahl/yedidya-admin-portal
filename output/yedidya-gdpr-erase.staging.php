<?php
/**
 * Plugin Name: Yedidya GDPR Erase
 * Description: REST endpoint for full GDPR user erasure (WordPress + WooCommerce). Called by the Yedidya Admin Portal. Added by Michael Stahl for the rare case where someone invokes their GDPR "right to be forgotten". 
 * Version:     1.0
 * Author:      Yedidya Admin
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

add_action( 'rest_api_init', function () {
    register_rest_route( 'yedidya/v1', '/gdpr-erase', [
        'methods'             => 'POST',
        'callback'            => 'yedidya_gdpr_erase_user',
        'permission_callback' => function () {
            return current_user_can( 'delete_users' );
        },
        'args' => [
            'email' => [
                'required'          => true,
                'type'              => 'string',
                'sanitize_callback' => 'sanitize_email',
                'validate_callback' => function ( $val ) {
                    return is_email( $val );
                },
            ],
        ],
    ] );
} );


/**
 * Full GDPR erasure for a user identified by email.
 *
 * Steps:
 *   1. Erase WooCommerce customer data (orders, sessions, lookup table)
 *      using WooCommerce's own WC_Privacy_Erasers class — no WC files modified.
 *   2. Delete the WordPress user and all their content.
 *
 * Returns JSON: { success: bool, warnings: string[] }
 */
function yedidya_gdpr_erase_user( WP_REST_Request $request ) {
    $email    = $request->get_param( 'email' );
    $warnings = [];

    // --- Step 1: WooCommerce erasure ---
    if ( class_exists( 'WC_Privacy_Erasers' ) ) {
        $page = 1;
        do {
            $result = WC_Privacy_Erasers::customer_data_eraser( $email, $page );
            if ( ! empty( $result['messages'] ) ) {
                $warnings = array_merge( $warnings, $result['messages'] );
            }
            $page++;
        } while ( ! empty( $result['done'] ) && $result['done'] === false );
    } else {
        $warnings[] = 'WooCommerce not active — WooCommerce data not erased.';
    }

    // Also erase WooCommerce order data associated with this email
    if ( class_exists( 'WC_Privacy_Erasers' ) ) {
        $page = 1;
        do {
            $result = WC_Privacy_Erasers::order_data_eraser( $email, $page );
            if ( ! empty( $result['messages'] ) ) {
                $warnings = array_merge( $warnings, $result['messages'] );
            }
            $page++;
        } while ( ! empty( $result['done'] ) && $result['done'] === false );
    }

    // --- Step 2: Delete the WordPress user ---
    $user = get_user_by( 'email', $email );

    if ( ! $user ) {
        // No WP account — WooCommerce data erasure (guest orders) may still have run
        $warnings[] = "No WordPress account found for {$email} — only WooCommerce data was erased.";
        return rest_ensure_response( [
            'success'  => true,
            'warnings' => $warnings,
        ] );
    }

    // Prevent deleting the currently authenticated user or a super admin
    if ( $user->ID === get_current_user_id() ) {
        return new WP_Error(
            'cannot_delete_self',
            'Cannot delete the currently authenticated user.',
            [ 'status' => 403 ]
        );
    }
    if ( is_super_admin( $user->ID ) ) {
        return new WP_Error(
            'cannot_delete_admin',
            'Cannot delete a super admin user.',
            [ 'status' => 403 ]
        );
    }

    // Delete user + all their content (no reassign = delete content)
    require_once ABSPATH . 'wp-admin/includes/user.php';
    $deleted = wp_delete_user( $user->ID );

    if ( ! $deleted ) {
        return new WP_Error(
            'delete_failed',
            "Failed to delete WordPress user {$email}.",
            [ 'status' => 500 ]
        );
    }

    return rest_ensure_response( [
        'success'  => true,
        'warnings' => $warnings,
    ] );
}
