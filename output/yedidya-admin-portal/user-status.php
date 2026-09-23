<?php
/**
 * User approval status (New User Approve) — REST endpoints.
 * Loaded by yedidya-admin-portal.php.
 *
 * New User Approve stores each user's state in the user meta key
 * `pw_user_status` ('approved' / 'denied' / 'pending'). A user with no
 * meta value is treated as approved (same as the plugin itself does).
 *
 * Changes are written SILENTLY — the meta is updated directly, so New User
 * Approve's approve/deny emails are NOT sent to the user.
 *
 * ENDPOINTS
 *   POST /wp-json/yedidya/v1/user-status/lookup
 *     Body (JSON): { "emails": ["a@example.com", ...] }
 *     Response:    { "users": [ { "email", "id", "name", "status", "roles" } ],
 *                    "not_found": ["..."] }
 *
 *   POST /wp-json/yedidya/v1/user-status
 *     Body (JSON): { "email": "a@example.com", "status": "approved" | "denied" }
 *     Response:    { "success": true, "email", "id", "old_status", "status" }
 *
 *   Auth: WordPress application password with edit_users capability
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

// ---------------------------------------------------------------------------
// Register REST routes
// ---------------------------------------------------------------------------

add_action( 'rest_api_init', function () {
    $permission = function () {
        return current_user_can( 'edit_users' );
    };

    register_rest_route( 'yedidya/v1', '/user-status/lookup', [
        'methods'             => 'POST',
        'callback'            => 'yedidya_user_status_lookup_handler',
        'permission_callback' => $permission,
        'args' => [
            'emails' => [
                'required' => true,
                'type'     => 'array',
            ],
        ],
    ] );

    register_rest_route( 'yedidya/v1', '/user-status', [
        'methods'             => 'POST',
        'callback'            => 'yedidya_user_status_set_handler',
        'permission_callback' => $permission,
        'args' => [
            'email' => [
                'required'          => true,
                'type'              => 'string',
                'sanitize_callback' => 'sanitize_email',
                'validate_callback' => function ( $value ) {
                    return is_email( $value );
                },
            ],
            'status' => [
                'required' => true,
                'type'     => 'string',
                'enum'     => [ 'approved', 'denied' ],
            ],
        ],
    ] );
} );

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

if ( ! function_exists( 'yedidya_user_status_get' ) ) {
function yedidya_user_status_get( $user_id ) {
    $status = get_user_meta( $user_id, 'pw_user_status', true );
    return $status ? $status : 'approved';
}
}

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

if ( ! function_exists( 'yedidya_user_status_lookup_handler' ) ) {
function yedidya_user_status_lookup_handler( WP_REST_Request $request ) {
    $users     = [];
    $not_found = [];

    foreach ( (array) $request->get_param( 'emails' ) as $raw ) {
        $email = sanitize_email( (string) $raw );
        $user  = $email ? get_user_by( 'email', $email ) : false;
        if ( ! $user ) {
            $not_found[] = (string) $raw;
            continue;
        }
        $users[] = [
            'email'  => $user->user_email,
            'id'     => $user->ID,
            'name'   => $user->display_name,
            'status' => yedidya_user_status_get( $user->ID ),
            'roles'  => array_values( $user->roles ),
        ];
    }

    return rest_ensure_response( [
        'users'     => $users,
        'not_found' => $not_found,
    ] );
}
}

if ( ! function_exists( 'yedidya_user_status_set_handler' ) ) {
function yedidya_user_status_set_handler( WP_REST_Request $request ) {
    $email  = $request->get_param( 'email' );
    $status = $request->get_param( 'status' );

    $user = get_user_by( 'email', $email );
    if ( ! $user ) {
        return new WP_Error( 'user_not_found', "No user with email {$email}.", [ 'status' => 404 ] );
    }

    // Safety: never deny an administrator or the account making the request —
    // that would lock admins out of the site.
    if ( 'denied' === $status
         && ( in_array( 'administrator', (array) $user->roles, true )
              || get_current_user_id() === $user->ID ) ) {
        return new WP_Error( 'cannot_deny_admin', 'Administrators cannot be denied.', [ 'status' => 400 ] );
    }

    $old_status = yedidya_user_status_get( $user->ID );
    if ( $old_status !== $status ) {
        update_user_meta( $user->ID, 'pw_user_status', $status );
        // New User Approve caches status counts for the Users list filters.
        delete_transient( 'new_user_approve_user_statuses' );
    }

    return rest_ensure_response( [
        'success'    => true,
        'email'      => $user->user_email,
        'id'         => $user->ID,
        'old_status' => $old_status,
        'status'     => $status,
    ] );
}
}
