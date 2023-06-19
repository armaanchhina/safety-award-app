$(document).ready(function () {
  $("#quarterlyForm").on('submit', function (e) {
    e.preventDefault(); // Prevent the form from being submitted traditionally
    
    var year = $("#year").val();
    if (isNaN(year) || year.length !== 4) {
        alert("Invalid year format. Please enter a valid 4-digit year.");
        return;
    }

    $.ajax({
      url: '/',
      method: 'POST',
      data: $(this).serialize(),
      success: function (data) {
          if (data.error) {
              alert(data.error); // Show the error message if an error exists
          } else if (data.success) {
              var link = '/download/' + data.filename;
              var downloadButton = $('<button/>', {
                  text: 'Download File',
                  click: function() { window.location = link; }
              });
              $('body').append(downloadButton);
          } else {
              alert("An unknown error occurred.");
          }
      }
    });
  });
});
