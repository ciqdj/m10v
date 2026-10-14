// Acceptance is scoped to one save attempt and its exact source/configuration.
export function createFirmwareSaveGate({dialog,trigger,cancel,confirm,readSnapshot,save}) {
 let snapshot=null,busy=false;
 const current=()=>snapshot&&JSON.stringify(readSnapshot())===JSON.stringify(snapshot);
 const dismiss=()=>{snapshot=null;if(dialog.open)dialog.close();trigger.focus({preventScroll:true});};
 cancel.addEventListener('click',dismiss);
 dialog.addEventListener('cancel',()=>{snapshot=null;trigger.focus({preventScroll:true});});
 dialog.addEventListener('close',()=>{snapshot=null;});
 confirm.addEventListener('click',async()=>{
  if(busy||!dialog.open||!current())return dismiss();
  const accepted=snapshot;busy=true;confirm.disabled=true;dialog.close();snapshot=null;
  try{await save(accepted);}finally{busy=false;confirm.disabled=false;trigger.focus({preventScroll:true});}
 });
 return {open(){if(busy||dialog.open||trigger.disabled)return;snapshot=readSnapshot();dialog.showModal();cancel.focus();}};
}
