navigation_link_=document.getElementById('navbarDropdownMenuLink');
dropdownMenu_=document.getElementById('dropdown-menu');
navigation_dropdown_ = bootstrap.Dropdown.getOrCreateInstance(navigation_link_);

document.querySelector('[aria-controls="navbarNavDropdown"]').addEventListener('click',()=>{
    if (!dropdownMenu_.classList.contains('show')) {
      setTimeout(()=>{navigation_dropdown_.show()}, 0);
    } // don't hide as that will conflict with native handling
});

window.matchMedia("(max-width: 992px)").addEventListener('change', e => {
  if (!e.matches) { // switched to desktop mode
    dropdownMenu_.style.marginTop = ""; // reset margin
    dropdownMenu_.style.marginLeft = "";
  } else {
    let toggler=document.getElementById('navbarNav-toggler').getBoundingClientRect();
    dropdownMenu_.style.marginTop = toggler.height/2+"px";
    dropdownMenu_.style.marginLeft = "-"+toggler.width+"px";
  }
});
