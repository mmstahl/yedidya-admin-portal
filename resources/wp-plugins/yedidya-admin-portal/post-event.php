<?php
/**
 * Post Event — WPML translation duplication endpoint.
 *
 * Registers:
 *   POST /wp-json/yedidya/v1/duplicate-post
 *
 * Body (JSON):
 *   source_post_id  (int)    — ID of the post to duplicate
 *   target_lang     (string) — WPML language code for the new post (e.g. "en")
 *
 * Response (JSON):
 *   { "id": <int>, "link": "<string>" }
 *
 * The endpoint creates a copy of the source post and links it as a WPML
 * translation sibling via wpml_set_element_language_details.  This is more
 * reliable than passing icl_translation_of through the standard WP REST API,
 * which WPML ignores on some versions.
 *
 * Requires: WPML (tested with 4.x+)
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

add_action( 'rest_api_init', 'yedidya_register_post_event_routes' );

function yedidya_register_post_event_routes() {
    register_rest_route(
        'yedidya/v1',
        '/duplicate-post',
        [
            'methods'             => 'POST',
            'callback'            => 'yedidya_duplicate_post_callback',
            'permission_callback' => function () {
                return current_user_can( 'edit_posts' );
            },
            'args' => [
                'source_post_id' => [
                    'required'          => true,
                    'type'              => 'integer',
                    'sanitize_callback' => 'absint',
                    'description'       => 'ID of the post to duplicate as a translation.',
                ],
                'target_lang' => [
                    'required'          => true,
                    'type'              => 'string',
                    'sanitize_callback' => 'sanitize_text_field',
                    'description'       => 'WPML language code for the new post (e.g. "en").',
                ],
            ],
        ]
    );
}

function yedidya_duplicate_post_callback( WP_REST_Request $request ) {
    $source_id   = $request->get_param( 'source_post_id' );
    $target_lang = $request->get_param( 'target_lang' );

    // Require WPML — the wpml_element_trid filter is a reliable presence check.
    if ( ! has_filter( 'wpml_element_trid' ) ) {
        return new WP_Error(
            'wpml_missing',
            'WPML is not active on this site. Cannot create a linked translation.',
            [ 'status' => 501 ]
        );
    }

    $source_post = get_post( $source_id );
    if ( ! $source_post ) {
        return new WP_Error(
            'not_found',
            "Post {$source_id} not found.",
            [ 'status' => 404 ]
        );
    }

    $element_type = 'post_' . $source_post->post_type;

    // Get source language details (language code + translation group ID).
    $source_lang_details = apply_filters( 'wpml_element_language_details', null, [
        'element_id'   => $source_id,
        'element_type' => $element_type,
    ] );
    $source_lang = $source_lang_details ? $source_lang_details->language_code : 'he';

    // trid = translation group — links all language versions of the same post.
    $trid = apply_filters( 'wpml_element_trid', null, $source_id, $element_type );

    // Create the new post (content is identical to source; user will edit it
    // via the portal's English tab after creation).
    $new_post_id = wp_insert_post(
        [
            'post_title'   => $source_post->post_title,
            'post_content' => $source_post->post_content,
            'post_status'  => $source_post->post_status,
            'post_type'    => $source_post->post_type,
            'post_author'  => get_current_user_id(),
        ],
        true  // return WP_Error on failure
    );

    if ( is_wp_error( $new_post_id ) ) {
        return new WP_Error(
            'insert_failed',
            $new_post_id->get_error_message(),
            [ 'status' => 500 ]
        );
    }

    // Copy categories from the source post.
    $cat_ids = wp_get_post_categories( $source_id, [ 'fields' => 'ids' ] );
    if ( ! empty( $cat_ids ) ) {
        wp_set_post_categories( $new_post_id, $cat_ids );
    }

    // Register the new post as a WPML translation sibling of the source.
    // This is the key step — it assigns the language AND links both posts
    // in the same translation group so WPML shows the language switcher.
    do_action( 'wpml_set_element_language_details', [
        'element_id'           => $new_post_id,
        'element_type'         => $element_type,
        'trid'                 => $trid,
        'language_code'        => $target_lang,
        'source_language_code' => $source_lang,
    ] );

    return rest_ensure_response( [
        'id'   => $new_post_id,
        'link' => get_permalink( $new_post_id ),
    ] );
}
