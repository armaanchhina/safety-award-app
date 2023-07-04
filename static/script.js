$(document).ready(function () {
  $("#quarterlyForm").on('submit', function (e) {
    e.preventDefault(); // Prevent the form from being submitted traditionally

    const year = $("#year").val();
    const quarter = $("#quarter").val();
    const driverId = $("#id").val() || 'none';  // If driverId is empty, default to 'none'
    const action = $("#action").val();

  
    let redirectUrl = `/bonus_chart/${quarter}/${year}/${driverId}`;

    if (action === "plot") {
      // Redirect to the plot URL
      window.location.href = redirectUrl;
      return;
    }
    if (action === "scorecard") {
      // Redirect to the scorecard URL
      window.location.href = `/scorecard/${quarter}/${year}/${driverId}`;
      return;
    }

    if (action === "piegraph") {
      // Redirect to the pie URL
      window.location.href = `/pie/${quarter}/${year}`;
      return;
    }

    // If the action is not "plot", proceed with the download action
    performAjaxRequest(year, quarter);
  });

  function performAjaxRequest(year, quarter) {
    $.ajax({
      url: '/',
      method: 'POST',
      data: $("#quarterlyForm").serialize(),
      beforeSend: function () {
        $("#loading").show();
      },
      complete: function () {
        $("#loading").hide();
      },
      success: function (data) {
        // console.log(data); // Log data to console

        if (data.error) {
          alert(data.error); // Show the error message if an error exists
        } else if (data.success) {
          const link = '/download/' + data.filename;

          // Update the href attribute and text of the download link
          $('#downloadLink').attr('href', link).text(`Download ${data.filename}`);

          // Show the download modal
          $('#downloadModal').modal('show');
        } else {
          alert("An unknown error occurred.");
        }
      },
      error: function (xhr, status, error) {
        // Alert any Ajax error
        alert("Ajax request failed: " + error);
      }
    });
  }
});
