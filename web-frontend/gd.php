<?php
/* 
 * render(myMap) - (c)2011-2018 Ferenc Veres
 * Licensed under GPL v3
 * 
 * This file is just the CAPCHA server side 
 */
session_start();

$chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjklmnpqrstuvwxyz23456789";
$code = substr(str_shuffle($chars), 0, 5);
$_SESSION["code"] = $code;
produceCaptchaImage($code);

//http://www.script-tutorials.com/how-to-create-captcha-in-php-using-gd-library/
function produceCaptchaImage($text) {
    // constant values
    $backgroundSizeX = 2000;
    $backgroundSizeY = 350;
    $sizeX = 200;
    $sizeY = 50;
    $fontFile = "fonts/Montserrat-Regular.ttf";
    $textLength = strlen($text);

    // generate random security values
    $backgroundOffsetX = rand(0, $backgroundSizeX - $sizeX - 1);
    $backgroundOffsetY = rand(0, $backgroundSizeY - $sizeY - 1);
    $angle = rand(-5, 5);
    $fontColorR = rand(0, 127);
    $fontColorG = rand(0, 127);
    $fontColorB = rand(0, 127);

    $fontSize = rand(14, 24);
    $textX = rand(0, (int)($sizeX - 0.9 * $textLength * $fontSize)); // these coefficients are empiric
    $textY = rand((int)(1.25 * $fontSize), (int)($sizeY - 0.2 * $fontSize)); // don't try to learn how they were taken out

    $gdInfoArray = gd_info();
    if (! $gdInfoArray['PNG Support'])
        return false;

    // create image with background
    $src_im = imagecreatefrompng( "images/captcha_bg.png");
    if (function_exists('imagecreatetruecolor')) {
        // this is more qualitative function, but it doesn't exist in old GD
        $dst_im = imagecreatetruecolor($sizeX, $sizeY);
        $resizeResult = imagecopyresampled($dst_im, $src_im, 0, 0, $backgroundOffsetX, $backgroundOffsetY, $sizeX, $sizeY, $sizeX, $sizeY);
    } else {
        // this is for old GD versions
        $dst_im = imagecreate( $sizeX, $sizeY );
        $resizeResult = imagecopyresized($dst_im, $src_im, 0, 0, $backgroundOffsetX, $backgroundOffsetY, $sizeX, $sizeY, $sizeX, $sizeY);
    }

    if (! $resizeResult)
        return false;

    // write text on image
    if (! function_exists('imagettftext'))
        return false;
    $color = imagecolorallocate($dst_im, $fontColorR, $fontColorG, $fontColorB);
    imagettftext($dst_im, $fontSize, -$angle, $textX, $textY, $color, $fontFile, $text);

    // output header
    header("Content-Type: image/png");

    // output image
    imagepng($dst_im);

    // free memory
    imagedestroy($src_im);
    imagedestroy($dst_im);

    return true;
}
?>
