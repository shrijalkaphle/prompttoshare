
  document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("myForm");
    var loader = document.getElementById("loader");

    form.addEventListener("submit", function () {
      loader.style.display = "block";
    });
  });

$(function() {


  var siteMenuClone = function() {

    $('.js-clone-nav').each(function() {
      var $this = $(this);
      $this.clone().attr('class', 'site-nav-wrap').appendTo('.site-mobile-menu-body');
    });


    setTimeout(function() {
      
      var counter = 0;
      $('.site-mobile-menu .has-children').each(function(){
        var $this = $(this);
        
        $this.prepend('<span class="arrow-collapse collapsed">');

        $this.find('.arrow-collapse').attr({
          'data-toggle' : 'collapse',
          'data-target' : '#collapseItem' + counter,
        });

        $this.find('> ul').attr({
          'class' : 'collapse',
          'id' : 'collapseItem' + counter,
        });

        counter++;

      });

    }, 1000);

    $('body').on('click', '.arrow-collapse', function(e) {
      var $this = $(this);
      if ( $this.closest('li').find('.collapse').hasClass('show') ) {
        $this.removeClass('active');
      } else {
        $this.addClass('active');
      }
      e.preventDefault();  
      
    });

    $(window).resize(function() {
      var $this = $(this),
        w = $this.width();

      if ( w > 768 ) {
        if ( $('body').hasClass('offcanvas-menu') ) {
          $('body').removeClass('offcanvas-menu');
        }
      }
    })

    $('body').on('click', '.js-menu-toggle', function(e) {
      var $this = $(this);
      e.preventDefault();

      if ( $('body').hasClass('offcanvas-menu') ) {
        $('body').removeClass('offcanvas-menu');
        $this.removeClass('active');
      } else {
        $('body').addClass('offcanvas-menu');
        $this.addClass('active');
      }
    }) 

    // click outisde offcanvas
    $(document).mouseup(function(e) {
      var container = $(".site-mobile-menu");
      if (!container.is(e.target) && container.has(e.target).length === 0) {
        if ( $('body').hasClass('offcanvas-menu') ) {
          $('body').removeClass('offcanvas-menu');
        }
      }
    });
  }; 
  siteMenuClone();

});



// Search filter for prompt on generate tab
function filterUserButtons() {
  var input, filter, radios, span, i, txtValue;
  input = document.getElementById("userSearch");
  filter = input.value.toLowerCase();
  radios = document.getElementsByClassName("user");

  for (i = 0; i < radios.length; i++) {
    span = radios[i].getElementsByTagName("span")[0];
    txtValue = span.textContent || span.innerText;
    if (txtValue.toLowerCase().indexOf(filter) > -1) {
      radios[i].style.display = "";
    } else {
      radios[i].style.display = "none";
    }
  }
}

// Function to show all radio buttons at the start
function showAllUserButtons() {
  var radios = document.getElementsByClassName("user");
  for (var i = 0; i < radios.length; i++) {
    radios[i].style.display = "";
  }
}

showAllUserButtons();



// function to show search data top-nav bar
function myFunction() {
    var input, filter, ul, li, a, i, txtValue;
    input = document.getElementById("myInput");
    filter = input.value.toUpperCase();
    ul = document.getElementById("myUL");

    // Show or hide the list based on whether there is any input
    if (filter.trim() === '') {
        ul.style.display = "none";
        return;
    } else {
        ul.style.display = "block";
    }

    // Make an API call to your Flask app
    fetch(`/api/users?q=${filter}`)
    .then(response => response.json())
    .then(data => {
        // Update the list of names with the API response
        ul.innerHTML = '';
        data.forEach(user => {
          ul.innerHTML += `<li><a href="/profile/${user.user_id}">${user.name}</a></li>`;
        });
    })
    .catch(error => {
        console.error('Error fetching data:', error);
    });
}


    // Function to hide the success alert after 5 seconds
    setTimeout(function() {
        const successAlert = document.getElementById('success-alert');
        if (successAlert) {
            successAlert.style.display = 'none';
        }
    }, 5000);

    // Function to hide the error alert after 5 seconds
    setTimeout(function() {
        const errorAlert = document.getElementById('error-alert');
        if (errorAlert) {
            errorAlert.style.display = 'none';
        }
    }, 5000);


    function openSearch() {
  document.getElementById("myOverlay").style.display = "block";
}

function closeSearch() {
  document.getElementById("myOverlay").style.display = "none";
}

