<?php
/**
 * DB Extract — REST endpoint.
 * Loaded by yedidya-admin-portal.php.
 *
 * Exposes a protected REST API endpoint that returns all users with
 * a caller-specified set of fields from wp_users and wp_usermeta.
 *
 * ENDPOINT
 *   GET /wp-json/yedidya/v1/db-extract?fields=user_email,first_name,last_name
 *   Auth: WordPress application password with edit_users capability
 *
 * Fields that match a wp_users column are fetched directly.
 * 'role' is a virtual field resolved from wp_capabilities.
 * All other field names are treated as usermeta keys.
 *
 * Recognised wp_users columns:
 *   ID, user_login, user_nicename, user_email, user_url,
 *   user_registered, user_status, display_name
 *
 * (user_pass is intentionally excluded.)
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

// wp_users columns that may be requested. user_pass excluded deliberately.
$GLOBALS['yedidya_users_columns'] = array(
    'ID', 'user_login', 'user_nicename', 'user_email',
    'user_url', 'user_registered', 'user_status', 'display_name',
);

add_action( 'rest_api_init', function () {
    register_rest_route( 'yedidya/v1', '/db-extract', array(
        'methods'             => 'GET',
        'callback'            => 'yedidya_db_extract',
        'permission_callback' => 'yedidya_check_permission',
        'args'                => array(
            'fields' => array(
                'required'          => true,
                'validate_callback' => function ( $param ) {
                    return is_string( $param ) && strlen( trim( $param ) ) > 0;
                },
                // Don't sanitize here — sanitize_text_field strips parentheses
                // and other characters that appear in some meta key names.
                'sanitize_callback' => function ( $param ) { return $param; },
            ),
        ),
    ) );
} );

function yedidya_db_extract( WP_REST_Request $request ) {
    $allowed_columns = $GLOBALS['yedidya_users_columns'];

    // Parse the comma-delimited field list.
    $requested = array_values( array_filter(
        array_map( 'trim', explode( ',', $request->get_param( 'fields' ) ) )
    ) );

    if ( empty( $requested ) ) {
        return new WP_Error( 'no_fields', 'No fields specified.', array( 'status' => 400 ) );
    }

    // Categorise each requested field.
    $users_columns = array();
    $meta_keys     = array();
    $wants_role    = false;

    foreach ( $requested as $field ) {
        if ( $field === 'role' ) {
            $wants_role = true;
        } elseif ( in_array( $field, $allowed_columns, true ) ) {
            $users_columns[] = $field;
        } else {
            $meta_keys[] = $field;
        }
    }

    // Always fetch ID so we can look up usermeta / capabilities.
    $fetch_fields = array_unique( array_merge( array( 'ID' ), $users_columns ) );

    $users = get_users( array(
        'number' => -1,
        'fields' => $fetch_fields,
    ) );

    $result = array();

    foreach ( $users as $user ) {
        $row = array();

        foreach ( $requested as $field ) {
            if ( $field === 'role' ) {
                // wp_capabilities is auto-unserialized by WordPress into an array
                // like ['subscriber' => true]. Return the first (primary) role.
                $caps  = get_user_meta( $user->ID, 'wp_capabilities', true );
                $roles = is_array( $caps ) ? array_keys( $caps ) : array();
                $row['role'] = ! empty( $roles ) ? $roles[0] : '';
            } elseif ( in_array( $field, $users_columns, true ) ) {
                $row[ $field ] = isset( $user->$field ) ? (string) $user->$field : '';
            } else {
                $value = get_user_meta( $user->ID, $field, true );
                $row[ $field ] = ( $value === false || $value === null ) ? '' : (string) $value;
            }
        }

        $result[] = $row;
    }

    return rest_ensure_response( $result );
}
