<?php
/**
 * DB Extract — REST endpoint.
 * Loaded by yedidya-admin-portal.php.
 *
 * GET /wp-json/yedidya/v1/db-extract?fields=first_name,last_name,role
 * GET /wp-json/yedidya/v1/db-extract?fields=first_name,last_name&gender=male
 * GET /wp-json/yedidya/v1/db-extract?fields=first_name,last_name&privacy=Yes
 * Auth: WordPress application password with edit_users capability
 *
 * 'role' is a virtual field resolved from wp_capabilities.
 * Fields matching a wp_users column are fetched directly.
 * All other fields are treated as usermeta keys.
 * user_pass is intentionally not available.
 *
 * gender (optional): 'male' or 'female'. When set, only users/partners of that
 * gender are returned. A WP account can produce two rows if both the user and
 * their partner share the same gender. For partner rows, the following fields
 * are remapped to partner-specific meta keys:
 *   first_name  → partnerfirst
 *   last_name   → partnerlast
 *   usercast    → partnercast
 *   hebrewname  → partnerhebname
 *   bmitzvah    → partnerbmparsha
 * Every row includes a 'record_type' field: 'user' or 'partner'.
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
                'gender' => array(
                    'required'          => false,
                    'type'              => 'string',
                    'enum'              => array( 'male', 'female' ),
                    'sanitize_callback' => 'sanitize_text_field',
                ),
                'privacy' => array(
                    'required'          => false,
                    'type'              => 'string',
                    'enum'              => array( 'Yes', 'No' ),
                    'sanitize_callback' => 'sanitize_text_field',
                ),
            ),
        ) );
    }
}

if ( ! function_exists( 'yedidya_db_extract_callback' ) ) {
    function yedidya_db_extract_callback( WP_REST_Request $request ) {
        $users_columns = array(
            'ID', 'user_login', 'user_nicename', 'user_email',
            'user_url', 'user_registered', 'user_status', 'display_name',
        );

        // Fields remapped to partner-specific meta keys in partner rows.
        $partner_field_map = array(
            'first_name' => 'partnerfirst',
            'last_name'  => 'partnerlast',
            'usercast'   => 'partnercast',
            'hebrewname' => 'partnerhebname',
            'bmitzvah'   => 'partnerbmparsha',
        );

        $raw       = $request->get_param( 'fields' );
        $requested = array_values( array_filter(
            array_map( 'trim', explode( ',', $raw ) )
        ) );

        if ( empty( $requested ) ) {
            return new WP_Error( 'no_fields', 'No fields specified.', array( 'status' => 400 ) );
        }

        // API accepts 'male'/'female'; DB stores 'M'/'F'.
        $gender_param  = $request->get_param( 'gender' );
        $gender_filter = $gender_param ? strtoupper( $gender_param[0] ) : null; // 'M' or 'F'

        // API accepts 'Yes'/'No'; DB stores 'Yes'/'No' (case-insensitive match).
        $privacy_filter = $request->get_param( 'privacy' ); // 'Yes', 'No', or null

        // Categorise each requested field.
        $col_fields = array();
        $wants_role = false;

        foreach ( $requested as $field ) {
            if ( $field === 'role' ) {
                $wants_role = true;
            } elseif ( in_array( $field, $users_columns, true ) ) {
                $col_fields[] = $field;
            }
        }

        $fetch_fields = array_unique( array_merge( array( 'ID' ), $col_fields ) );

        $users = get_users( array(
            'number' => -1,
            'fields' => $fetch_fields,
        ) );

        $result = array();

        foreach ( $users as $user ) {
            // Privacy filter applies to the whole account (both user and partner rows).
            if ( $privacy_filter ) {
                $account_privacy = (string) get_user_meta( $user->ID, 'contact_list_privacy_setting', true );
                if ( strcasecmp( $account_privacy, $privacy_filter ) !== 0 ) {
                    continue;
                }
            }

            if ( $gender_filter ) {
                $user_gender    = strtoupper( (string) get_user_meta( $user->ID, 'yourgender',    true ) );
                $partner_gender = strtoupper( (string) get_user_meta( $user->ID, 'partnergender', true ) );

                if ( $user_gender === $gender_filter ) {
                    $result[] = yedidya_build_extract_row(
                        $user, $requested, $col_fields, $wants_role, false, $partner_field_map
                    );
                }
                if ( $partner_gender === $gender_filter ) {
                    $result[] = yedidya_build_extract_row(
                        $user, $requested, $col_fields, $wants_role, true, $partner_field_map
                    );
                }
            } else {
                $result[] = yedidya_build_extract_row(
                    $user, $requested, $col_fields, $wants_role, false, $partner_field_map
                );
            }
        }

        return rest_ensure_response( $result );
    }
}

function yedidya_build_extract_row( $user, $requested, $col_fields, $wants_role, $is_partner, $partner_field_map ) {
    $row = array( 'record_type' => $is_partner ? 'partner' : 'user' );

    foreach ( $requested as $field ) {
        if ( $field === 'role' ) {
            $caps        = get_user_meta( $user->ID, 'wp_capabilities', true );
            $roles       = is_array( $caps ) ? array_keys( $caps ) : array();
            $row['role'] = ! empty( $roles ) ? $roles[0] : '';
        } elseif ( in_array( $field, $col_fields, true ) ) {
            $row[ $field ] = isset( $user->$field ) ? (string) $user->$field : '';
        } else {
            // For partner rows, remap fields that have a partner-specific meta key.
            $meta_key      = ( $is_partner && isset( $partner_field_map[ $field ] ) )
                ? $partner_field_map[ $field ]
                : $field;
            $value         = get_user_meta( $user->ID, $meta_key, true );
            $row[ $field ] = ( $value === false || $value === null ) ? '' : (string) $value;
        }
    }

    return $row;
}
