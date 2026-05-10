<?php
/**
 * Members list link shortcode — cache-busting.
 * Loaded by yedidya-admin-portal.php.
 *
 * Usage (on any WordPress page or post):
 *   [members_list_link]
 *   [members_list_link text="הורד רשימת חברים"]
 *
 * The link URL includes the PDF file's modification timestamp as a query
 * string (?v=...). When a new PDF is uploaded via SFTP, the timestamp
 * changes automatically — browsers always fetch the fresh file.
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

add_shortcode( 'members_list_link', 'yedidya_members_list_link_shortcode' );

function yedidya_members_list_link_shortcode( $atts ) {
    $atts = shortcode_atts(
        [ 'text' => 'רשימת חברים' ],
        $atts,
        'members_list_link'
    );

    $file_path = WP_CONTENT_DIR . '/uploads/members/members_list.pdf';
    $file_url  = content_url( '/uploads/members/members_list.pdf' );

    if ( ! file_exists( $file_path ) ) {
        return '<!-- members_list_link: file not found -->';
    }

    $version = filemtime( $file_path );

    return '<a href="' . esc_url( $file_url . '?v=' . $version ) . '">'
           . esc_html( $atts['text'] ) . '</a>';
}
