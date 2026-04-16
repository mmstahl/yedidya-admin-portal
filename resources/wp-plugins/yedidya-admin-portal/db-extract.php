<?php
/**
 * DB Extract — REST endpoint.
 * Loaded by yedidya-admin-portal.php.
 *
 * GET /wp-json/yedidya/v1/db-extract?fields=first_name,last_name,role
 * Auth: WordPress application password with edit_users capability
 *
 * 'role' is a virtual field resolved from wp_capabilities.
 * Fields matching a wp_users column are fetched directly.
 * All other fields are treated as usermeta keys.
 * user_pass is intentionally not available.
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

add_action( 'rest_api_init', 'yedidya_register_db_extract_route' );

if ( ! function_exists( 'yedidya_register_db_extract_route' ) ) {
    function yedidya_register_db_extract_route() {
        register_rest_route( 'yedidya/v1', '/db-extract', array(
            'methods'             => 'GET',
            'callback'            => 'yedidya_db_extract_callback',
            'permission_callback' => 'yedidya_check_permission',
            'args'                => array(
                'fields' => array(
                    'required' => true,
                ),
            ),
        ) );
    }
}

if ( ! function_exists( 'yedidya_db_extract_callback' ) ) {
    function yedidya_db_extract_callback( WP_REST_Request $request ) {
        // wp_users columns available for selection (user_pass excluded).
        $users_columns = array(
            'ID', 'user_login', 'user_nicename', 'user_email',
            'user_url', 'user_registered', 'user_status', 'display_name',
        );

        // Parse the comma-delimited field list.
        $raw = $request->get_param( 'fields' );
        $requested = array_values( array_filter(
            array_map( 'trim', explode( ',', $raw ) )
        ) );

        if ( empty( $requested ) ) {
            return new WP_Error( 'no_fields', 'No fields specified.', array( 'status' => 400 ) );
        }

        // Categorise each requested field.
        $col_fields  = array();
        $wants_role  = false;

        foreach ( $requested as $field ) {
            if ( $field === 'role' ) {
                $wants_role = true;
            } elseif ( in_array( $field, $users_columns, true ) ) {
                $col_fields[] = $field;
            }
        }

        // Always fetch ID; add any requested wp_users columns.
        $fetch_fields = array_unique( array_merge( array( 'ID' ), $col_fields ) );

        $users = get_users( array(
            'number' => -1,
            'fields' => $fetch_fields,
        ) );

        $result = array();

        foreach ( $users as $user ) {
            $row = array();

            foreach ( $requested as $field ) {
                if ( $field === 'role' ) {
                    $caps  = get_user_meta( $user->ID, 'wp_capabilities', true );
                    $roles = is_array( $caps ) ? array_keys( $caps ) : array();
                    $row['role'] = ! empty( $roles ) ? $roles[0] : '';
                } elseif ( in_array( $field, $col_fields, true ) ) {
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
}
