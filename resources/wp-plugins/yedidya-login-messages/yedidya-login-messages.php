<?php
/**
 * Plugin Name: Yedidya Login Messages
 * Description: Replaces the "New User Approve" plugin's pending/denied login messages with bilingual (Hebrew/English) text tailored to Yedidya, matching the visitor's WPML language. Added by Michael Stahl.
 * Version:     1.0.0
 * Author:      Michael Stahl
 *
 * REQUIRES: "New User Approve" plugin (free version) active.
 *   Hooks its documented filters — does not touch its authentication logic.
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

// ---------------------------------------------------------------------------
// Language detection
// ---------------------------------------------------------------------------

if ( ! function_exists( 'yedidya_login_message_language' ) ) {
function yedidya_login_message_language() {
    $lang = apply_filters( 'wpml_current_language', null );
    return ( $lang === 'en' ) ? 'en' : 'he'; // default to Hebrew
}
}

// ---------------------------------------------------------------------------
// Message text
// ---------------------------------------------------------------------------

if ( ! function_exists( 'yedidya_pending_login_message' ) ) {
function yedidya_pending_login_message() {
    if ( yedidya_login_message_language() === 'en' ) {
        return '<strong>ERROR</strong>: Your account has not yet been approved by the website administrator. '
            . 'If this is urgent, or if two days have already passed and you still cannot log in, '
            . 'please contact Michael Stahl (054-7887488 or michael.m.stahl@gmail.com).';
    }

    return '<strong>שגיאה</strong>: החשבון שלך עדיין לא אושר על ידי מנהל האתר. '
        . 'אם זה דחוף, או אם כבר עברו יומיים ועדיין אי אפשר להכנס, '
        . 'צור קשר עם מיכאל שטאל (054-7887488 או michael.m.stahl@gmail.com).';
}
}

if ( ! function_exists( 'yedidya_denied_login_message' ) ) {
function yedidya_denied_login_message() {
    if ( yedidya_login_message_language() === 'en' ) {
        return '<strong>ERROR</strong>: Your account has been blocked because you have not yet paid your membership dues. '
            . 'Logging into the website allows downloading details of community members, and due to privacy laws in the '
            . 'State of Israel, we are only permitted to share member details with other members of the community. '
            . 'For further details, please contact Michael Stahl (054-7887488 or michael.m.stahl@gmail.com).';
    }

    return '<strong>שגיאה</strong>: החשבון שלך נחסם כיוון שעדיין לא שילמת את דמי החבר. '
        . 'כניסה לאתר מאפשרת הורדה של פרטי החברים בקהילה, ועקב חוקי הפרטיות במדינת ישראל מותר לנו לחלוק את פרטי החברים '
        . 'רק עם חברים אחרים בקהילה. לפרטים נוספים צור קשר עם מיכאל שטאל (054-7887488 או michael.m.stahl@gmail.com).';
}
}

// ---------------------------------------------------------------------------
// Hook into New User Approve's message filters
// ---------------------------------------------------------------------------

add_filter( 'new_user_approve_pending_error', 'yedidya_pending_login_message' );
add_filter( 'new_user_approve_denied_error', 'yedidya_denied_login_message' );
