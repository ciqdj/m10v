// Keep each new step's title visible when switching from a long settings page.
export function focusWorkbenchHeading(heading,viewport=window){
 if(!heading)return;
 heading.tabIndex=-1;
 heading.focus({preventScroll:true});
 const bounds=heading.getBoundingClientRect();
 if(bounds.top<16||bounds.bottom>viewport.innerHeight){
  const page=heading.closest('[data-page]')||heading;
  viewport.scrollTo({top:Math.max(0,page.getBoundingClientRect().top+viewport.scrollY-24),behavior:'instant'});
 }
}
