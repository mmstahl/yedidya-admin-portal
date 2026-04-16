<?php
/**
 * Member export — REST endpoint.
 * Loaded by yedidya-admin-portal.php.
 *
 * ENDPOINT
 *   GET /wp-json/yedidya/v1/members
 *   Auth: WordPress application password with edit_users capability
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

add_action( 'rest_api_init', function () {
    register_rest_route( 'yedidya/v1', '/members', array(
        'methods'             => 'GET',
        'callback'            => 'yedidya_get_members',
        'permission_callback' => 'yedidya_check_permission',
    ) );
} );

if ( ! function_exists( 'yedidya_check_permission' ) ) {
    function yedidya_check_permission() {
        return current_user_can( 'edit_users' );
    }
}

if ( ! function_exists( 'yedidya_get_members' ) ) {
    function yedidya_get_members( $request ) {
        $meta_keys = array(
            'havepartner',
            'partnerfirst',
            'partnerlast',
            'partneremail',
            'cellphone1',
            'partnerphone',
            'homephone',
            'home_address',
            'yourgender',
            'partnergender',
            'contact_list_privacy_setting',
            'privacy_approval',
        );

        $users = get_users( array(
            'number' => -1,
            'fields' => array( 'ID', 'user_login', 'user_email' ),
        ) );

        $result = array();

        foreach ( $users as $user ) {
            $meta = array();
            foreach ( $meta_keys as $key ) {
                $value = get_user_meta( $user->ID, $key, true );
                $meta[ $key ] = ( $value === false || $value === null ) ? '' : $value;
            }

            $result[] = array(
                'user_login'                    => $user->user_login,
                'user_email'                    => $user->user_email,
                'first_name'                    => get_user_meta( $user->ID, 'first_name', true ) ?: '',
                'last_name'                     => get_user_meta( $user->ID, 'last_name', true ) ?: '',
                'havepartner'                   => $meta['havepartner'],
                'partnerfirst'                  => $meta['partnerfirst'],
                'partnerlast'                   => $meta['partnerlast'],
                'partneremail'                  => $meta['partneremail'],
                'cellphone1'                    => $meta['cellphone1'],
                'partnerphone'                  => $meta['partnerphone'],
                'homephone'                     => $meta['homephone'],
                'home_address'                  => $meta['home_address'],
                'yourgender'                    => $meta['yourgender'],
                'partnergender'                 => $meta['partnergender'],
                'contact_list_privacy_setting'  => $meta['contact_list_privacy_setting'],
                'privacy_approval'              => $meta['privacy_approval'],
            );
        }

        return rest_ensure_response( $result );
    }
}
