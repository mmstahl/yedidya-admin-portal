<?php
/**
 * Plugin Name: Yedidya Admin Portal
 * Description: Server-side support for the Yedidya Admin Portal desktop app. Includes GDPR user erasure endpoint and members list shortcode. Added by Michael Stahl.
 * Version:     1.0.0
 * Author:      Michael Stahl
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

require_once plugin_dir_path( __FILE__ ) . 'member-export.php';
require_once plugin_dir_path( __FILE__ ) . 'gdpr-erase.php';
require_once plugin_dir_path( __FILE__ ) . 'members-list-link-shortcode.php';