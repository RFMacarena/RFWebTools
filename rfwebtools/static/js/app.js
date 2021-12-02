function toggle(source) {
  checkboxes = document.querySelectorAll("input[type='checkbox']");
  for(var i=0, n=checkboxes.length;i<n;i++) {
  if(checkboxes[i].name.startsWith(source.name))
    checkboxes[i].checked = source.checked;}
}


