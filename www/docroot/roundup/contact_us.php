<?PHP

$pagetitle = "Support Request Form";
require('roundup/roundup_header.php');

// It would be good to include this again at some point for consistency
#require 'global.php';

define('RT_SUBMIT_EMAIL', 'submit-cbi@rt.med.harvard.edu');

// If the user just submitted, set some things in cookies so they don't have
// to re-enter their contact information every time.

if ( isset( $_POST['submit'] ) ) {
    foreach ( array( 'name_first', 'name_last', 'email', 'phone',
                     'buildingroom' ) as $cookie ) {
        setcookie( $cookie, $_POST[$cookie],
                   time() + ( 60 * 60 * 24 * 30 ), '', $_SERVER['HTTP_HOST'] );
    }
}

// If the user clicked "Clear", delete the cookies and POST variables.

if ( isset( $_POST['clear'] ) ) {

    foreach ( array( 'name_first', 'name_last', 'email', 'phone',

                     'buildingroom' ) as $var ) {

        setcookie( $var, $_POST[$var],

                   time() - 3600, '', $_SERVER['HTTP_HOST'] );

        unset( $_POST[$var] );

    }



    foreach ( array( 'subject', 'description' ) as $var ) {

        unset( $_POST[$var] );

    }

}

?>


<Table width=700 border=0 align="CENTER" >

 <TR><!-- <TD align="left" valign="top" width="200">
 <?PHP // require_once('buildmenu.php'); ?>
 
 </TD> -->

<TD align="left" valign="top">

<div align="left"><h3>Contact Us</h3></div>

<hr noshade size="1">



<?php



///////////////////////////////////////////////////////////////////////////////

// Lists

///////////////////////////////////////////////////////////////////////////////

// require 'customers.php';



$fields = array(

                'name_first'   => 'First Name',

                'name_last'    => 'Last Name',

                'email'        => 'E-mail Address'

                                  .'<br>(<b>please enter carefully</b>)',

                'phone'        => 'Phone Number',

                'buildingroom' => 'Building/Room',

/*                 'customer'     => 'Department, Lab, or Group', */

                'subject'      => 'Subject'

                );



///////////////////////////////////////////////////////////////////////////////

/// Functions

///////////////////////////////////////////////////////////////////////////////

function error_check() {

    global $fields;



    while ( list( $name, $label ) = each( $fields ) ) {

        if ( $_POST[$name] == '' ) {

            $errors[$name] = 1;

        }

    }



/*     if ( $_POST['customer'] == '--' ) {

        $errors['customer'] = 1;

    } */



    if ( isset( $errors ) ) {

        $errors['error_messages'][] =

'You left some fields blank.  They are marked in red.';

    }



    if ( ! ereg( '^[^@ ]+@[^@ ]+\.[^@ \.]+$', $_POST['email'] ) ) {

        $errors['email'] = 1;

        $errors['error_messages'][] =

'Your e-mail address doesn\'t appear to be valid.  Make sure you enter

your complete address in the form <tt>user@hostname</tt>.  A valid

e-mail address does not contain any spaces.';

    }



    if ( $_POST['description'] == '' ) {

        $errors['description'] = 1;

        $errors['error_messages'][] =

'You didn\'t enter a description of your request.';

    }



    if ( isset( $errors ) ) {

        return $errors;

    } else {

        return NULL;

    }

}



function print_form( $errors = NULL ) {

    global $fields, $customers;



    echo '



<p>Is something broken?  Do you just not understand how one of our applications works?  Are your results all screwy?</p>



<p>If so please take a minute to fill out the form below.  We appreciate your help and will do our best to resolve your issue as soon as possible.</p>



<form name="support" method="post">

 <table border="0" cellpadding="5" cellspacing="0" bordercolor="#CCCCCC" width="100%">

';



    reset( $fields );



    $bgcolor = '#EEEEEE';

    while ( list( $name, $label ) = each( $fields ) ) {



        if ( $bgcolor == '#EEEEEE' ) $bgcolor = '#FFFFFF';

        else                         $bgcolor = '#EEEEEE';



        if ( isset( $errors[$name] ) ) {

            $label = '<font color="red">'.$label.'</font>';

        }



         if ( $name == 'customer' ) {

            if ( isset( $_POST['customer'] ) ) {

                $customer = $_POST['customer'];

            } else if ( isset( $_COOKIE['customer'] ) ) {

                $customer = $_COOKIE['customer'];

            } else {

                $customer = '--';

            } 



            echo '

  <tr valign="middle" bgcolor="'.$bgcolor.'"> 

   <td>'.$label.'</td>

   <td>

    <select name="'.$name.'" size="1">';



            while ( list( $value, $label ) = each ( $customers ) ) {

                echo "\n" . '<option '

                    . ( ( $customer == $value ) ? ' selected' : '' )

                    . ' value="'.$value

                    . '">'.$label.'</option>';

            }



            echo '

    </select>

   </td>

  </tr>

';

        } else {

            if ( isset( $_POST[$name] ) ) {

                ${$name} = $_POST[$name];

            } else if ( isset( $_COOKIE[$name] ) ) {

                ${$name} = $_COOKIE[$name];

            } else {

                ${$name} = '';

            }



            echo '

  <tr valign="middle" bgcolor="'.$bgcolor.'">

   <td>'.$label.'</td>

   <td><input type="text" size="25" name="'.$name.'" value="'.${$name}.'"></td>

  </tr>

';

        }

    }

        

    echo '

 </table>



'.( isset( $errors['description'] ) ? '<font color="red">' : '' ).'

Below, please enter a description of your request.  Please be as

specific as possible.<br>

'.( isset( $errors['customer'] ) ? '</font>' : '' ).'



 <textarea name="description" cols="60" rows="10" wrap="physical">'.( isset( $_POST['description'] ) ? $_POST['description'] : '' ).'</textarea><br>

 <input type="submit" name="submit" value="Submit request"><br>

 <input type="submit" name="clear" value="Clear all fields"><br>

 <input type="reset" name="reset" value="Reset to saved values">

</form>

';

}





///////////////////////////////////////////////////////////////////////////////

// Main program flow

///////////////////////////////////////////////////////////////////////////////



if ( isset( $_POST['clear'] ) ) {

    foreach ( $fields as $field => $value ) {

        unset( $_COOKIE[$field] );

        unset( $_POST[$field] );

    }

}



if ( ! isset( $_POST['submit'] ) ) {

    print_form();

} else {

    // If the user just submitted, then use the values that were POSTed,

    // not the values from the user's cookies.

    foreach ( $fields as $field => $value ) {

        if ( isset( $_POST[$field] ) ) {

            ${$field} = $_POST[$field];

        } else if ( isset( $_COOKIE[$field] ) ) {

            ${$field} = $_COOKIE[$field];

        }

    }



    $errors = error_check();



    // If errors were detected, redisplay the form with information about them.

    if ( is_array( $errors ) ) {

        echo '

<p><font color="red">Please correct the following problems and re-submit.

<ul>

';

        while ( list( $x, $text ) = each ( $errors['error_messages'] ) ) {

            echo '<li>'.$text.'</li>';

        }

        echo '

</ul>

</font>';



        print_form( $errors );

    }



    // If the submission was error-free, construct and send the e-mail.

    else {

      // Only the production site should send mail to the production RT.

      // This should be adjusted if this form is moved or reused.

      $mailto = RT_SUBMIT_EMAIL;

      //if ( $_SERVER['HTTP_HOST'] == 'rodeo.med.harvard.edu' ) {

      //    $mailto = "submit-cbi@rt.med.harvard.edu";

      //} else {

      //    $mailto = "submit-cbi@dev.rt.med.harvard.edu";

      //}



        $message = 

"This ticket was submitted via http://".$_SERVER['HTTP_HOST'].$_SERVER['REQUEST_URI']."

-------------------------------------------------------------------------------

Requestor's contact information:



	$name_first $name_last <$email>

	Phone:			$phone

	Location:		$buildingroom

	Department/Lab/Group:	$customers[$customer]

-------------------------------------------------------------------------------



".$_POST['description']."

";



        mail( $mailto,

              stripslashes( $_POST['subject'] ),

              stripslashes( $message ),

              "From: $name_first $name_last <$email>\n"

              . "Reply-To: $name_first $name_last <$email>" );

        

        echo '

<p>Your request has been submitted.  You will receive a confirmation

message with your ticket number shortly.</p>



<p>You can now



<ul>



<li><a href="/roundup/contact_us.php">Submit another request.</a></li>



<li><a href="/">Return to the main page of our web site.</a></li>



</ul>



</p>

';

    }

}
?>

</TD>
</TR>
</Table>

<?PHP
require('roundup/roundup_footer.php');
?>
