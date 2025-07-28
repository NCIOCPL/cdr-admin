function change_file() {
  const select = document.getElementById("filename");
  const filename = select.options[select.selectedIndex].value ?? "";
  if (filename) {
    const session = document.querySelector("input[name='Session']").value ?? "";
    window.location.href = `EditConfig.py?Session=${session}&filename=${filename}`;
  }
}
