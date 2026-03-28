function start_server(completion_handler){
    fetch(`${location.origin}/testserver/start`,{method:'POST'}).then((resp)=>{
        const success=resp.ok;
        completion_handler(success);
    })
}

function stop_server(completion_handler){
    fetch(`${location.origin}/testserver/stop`,{method:'POST'}).then((resp)=>{
        const success=resp.ok;
        completion_handler(success);
    })
}

function start_server_clicked(){
    if(!confirm(`Are you sure you want to start the test server?`))return;
    let button=document.getElementById(`start-server`);
    button.disabled=true;
    button.innerText="Starting...";
    start_server((success)=>{
        if (success) {
            location.reload();
        } else {
            button.innerText="Failed";
            setTimeout(()=>{
                button.disabled=false;
                button.innerText="Start";
            },2000);
        }
    });
}

function stop_server_clicked(){
    if(!confirm(`Are you sure you want to stop the test server?`))return;
    let button=document.getElementById(`stop-server`);
    button.disabled=true;
    button.innerText="Stopping...";
    stop_server((success)=>{
        if (success) {
            location.reload();
        } else {
            button.innerText="Failed";
            setTimeout(()=>{
                button.disabled=false;
                button.innerText="Stop";
            },2000);
        }
    });
}