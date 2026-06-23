(function () {
  function getCookie(name) {
    var value = "; " + document.cookie;
    var parts = value.split("; " + name + "=");
    if (parts.length === 2) {
      return parts.pop().split(";").shift();
    }
    return "";
  }

  function uploadUrl(fileType) {
    if (fileType === "media") {
      return "/admin/tinymce/upload/video/";
    }
    return "/admin/tinymce/upload/image/";
  }

  window.streetServiceTinymceFilePicker = function (callback, value, meta) {
    var input = document.createElement("input");
    input.type = "file";
    input.accept = meta.filetype === "media" ? "video/*" : "image/*";

    input.onchange = function () {
      var file = input.files && input.files[0];
      if (!file) {
        return;
      }

      var formData = new FormData();
      formData.append("file", file);

      fetch(uploadUrl(meta.filetype), {
        method: "POST",
        body: formData,
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": getCookie("csrftoken"),
        },
      })
        .then(function (response) {
          return response.json().then(function (payload) {
            if (!response.ok) {
              throw new Error(payload.error || "上传失败");
            }
            return payload;
          });
        })
        .then(function (payload) {
          callback(payload.location, { title: file.name });
        })
        .catch(function (error) {
          window.alert(error.message || "上传失败");
        });
    };

    input.click();
  };
})();
