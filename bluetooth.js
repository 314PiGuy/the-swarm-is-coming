const xrpId = '51ff9301-d04e-4a0d-91c9-975fca9cdf95' //uuid of main xrp service

const button = document.getElementById('KavinBorderPatrol');
button.onclick = connect;

var device
var server;
var service;
var XRPcommands = [];

async function connect(){
    device = await navigator.bluetooth.requestDevice({ filters: [{ services: [xrpId] }] });
    server = await device.gatt.connect();
    service = await server.getPrimaryService(xrpId);
    const characteristic = await service.getCharacteristic('ed59696a-b609-4cea-a09a-5885cce3c5ca');
    XRPcommands.push(characteristic); //command characteristic
    characteristic.addEventListener('characteristicvaluechanged', handleNotif);
}

async function send(data){
    for (var c in XRPcommands){
        c.writeValueWithoutResponse(data);
    }
}

function handeNotif(e){
    let data = e.target.value.getUint8();
    const id = data[0];
    for (var x in XRPs){
        if (x.id == id) x.locked = false;
    }
    
}
