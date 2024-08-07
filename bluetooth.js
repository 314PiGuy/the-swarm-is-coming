const fish = '27df26c5-83f4-4964-bae0-d7b7cb0a1f54';
var device;
var server;
var service;
var dataLobber;
var bleUpdateInProgress = false;
var isConnectedBLE = false;
var button;

function createBleAgent() {
    button = document.getElementById('KavinBorderPatrol')


    button.onclick = changeBleState;
    button.ontouchend = changeBleState;
}

function displayBleStatus(status) {
    button.innerHTML = status;
    switch (status) {
        case 'Connecting':
            button.style.backgroundColor = 'grey';
            break;
        case 'Connected':
            button.style.backgroundColor = '#4dae50';
            break;
        case 'Disconnecting':
            button.style.backgroundColor = 'grey';
            break;
        case 'Not Connected':
            button.style.backgroundColor = 'grey';
            break;
        default:
            button.style.backgroundColor = '#eb5b5b';
    }
}


async function changeBleState() {
    if (bleUpdateInProgress) return
    bleUpdateInProgress = true;
    if (!isConnectedBLE) connectBLE();
    else disconnectBLE();
    bleUpdateInProgress = false;
}

async function connectBLE() {
    displayBleStatus('Connecting');

    try {
        device = await navigator.bluetooth.requestDevice({ filters: [{ services: [fish] }] });
        server = await device.gatt.connect();
        service = await server.getPrimaryService(fish);
        dataLobber = service.getCharacteristic('27df26c6-83f4-4964-bae0-d7b7cb0a1f54')
        await device.addEventListener('gattserverdisconnected', robotDisconnect);

        displayBleStatus('Connected');
        isConnectedBLE = true;

    } catch (error) {
        displayBleStatus("Error");
        console.error('Error:', error);
    }
}

async function disconnectBLE() {
    displayBleStatus('Disconnecting');
    try {
        await device.gatt.disconnect();

        displayBleStatus('Not Connected');
        isConnectedBLE = false;

    } catch (error) {
        displayBleStatus("Error");
        console.error('Error:', error);
    }
}

function robotDisconnect(event) {
    displayBleStatus('Not Connected');
    isConnectedBLE = false;
}

async function sendPacketBLE(byteArray) {
    if (!isConnectedBLE) return;
    if (bleUpdateInProgress) return;

    try {
        await dataLobber.writeValueWithoutResponse(byteArray);
    } catch (error) {
        console.error('Error:', error);
    }
}
