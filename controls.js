var XRPs = [];
var sprites = [];
selected = -1


var config = {
    type: Phaser.AUTO,
    width: 800,
    height: 800,
    physics: {
        default: 'arcade',
        arcade: {
            gravity: { y: 200 }
        }
    },
    scene: {
        preload: preload,
        create: create,
        update: update
    },
    fps: {
        target: 0,
        forceSetTimeout: true
    }
};

var game = new Phaser.Game(config);

class XRP {
    constructor(id, dir) {
        this.locked = false;
        this.id = id;
        this.dir = dir;
        this.command = {
            'vx': 0,
            'vy': 0,
            'vr': 0,
            'ticks': 0,
            'rticks': 0
        };
    }
}

function getAngle(x0, y0, x1, y1, dir) {
    var a = Math.atan(Math.abs(y1 - y0) / Math.abs(x1 - x0));
    if (x1 < x0) {
        a = Math.PI - a;
    }
    if (y1 > y0) {
        a = -a;
    }
    a *= 180/Math.PI;
    a -= dir;

    if (a > 0){
        a -= 360 * Math.floor(a/360);
    }
    else{
        a += 360 * Math.floor(a/-360);
    }
    if (Math.abs(a) <= 180) return a;
    else if (a > 0) return a - 360;
    else return a +360;
   
}

function preload() {
    this.load.image('rick', 'assets/rick.jpg');
    this.load.image('grass', 'assets/grass.png');
    this.load.audio('roll', 'assets/rick.mp3');
}

function create() {
    // const bgmusic = this.sound.add('roll');
    // bgmusic.loop = true;
    // bgmusic.play()
    
    this.grass = this.add.sprite(400, 400, 'grass').setInteractive();

    for (var n = 1; n < 4; n++){
        sprites.push(this.add.sprite(100*n, 100, 'rick').setInteractive());
        XRPs.push(new XRP(n, 0));
    }

    for (let i = 0; i < sprites.length; i++){
        sprites[i].on('pointerdown', function (pointer) {
            if (XRPs[i].locked == false) selected = i;
        });
    }

    this.grass.on('pointerdown', () => {
        if (selected != -1) {
            const dx = game.input.mousePointer.x - sprites[selected].x;
            const dy = game.input.mousePointer.y - sprites[selected].y;
            const h = Math.sqrt(dx ** 2 + dy ** 2);
            const sprite = sprites[selected];
            var angle = -(getAngle(sprite.x, sprite.y, game.input.mousePointer.x, game.input.mousePointer.y, XRPs[selected].dir));
            sendCommand(XRPs[selected].id, -angle, h);
            XRPs[selected].locked = true;
            XRPs[selected].command.rticks = Math.floor((angle) / 0.8);
            XRPs[selected].command.vr = 0.8;
            if (XRPs[selected].command.rticks < 0){
                XRPs[selected].command.rticks *= -1;
                XRPs[selected].command.vr *= -1;
            }
            XRPs[selected].command.vx = 2 * dx / h;
            XRPs[selected].command.vy = 2 * dy / h;
            XRPs[selected].command.ticks = Math.floor(h / 2);
            selected = -1;
        }
    })
}


function update() {
    for (var i = 0; i < XRPs.length; i++) {
        if (XRPs[i].command.rticks > 0) {
            XRPs[i].command.rticks--;
            sprites[i].angle += XRPs[i].command.vr;
            XRPs[i].dir -= XRPs[i].command.vr;
            if (XRPs[i].dir > 360) XRPs[i].dir -= 360;
            if (XRPs[i].dir < 360) XRPs[i].dir += 360;
        }
        else if (XRPs[i].command.ticks > 0) {
            XRPs[i].command.ticks--;
            sprites[i].x += XRPs[i].command.vx;
            sprites[i].y += XRPs[i].command.vy;
        }
    }
}

function sendCommand(id, turn, drive){
    const data = new Uint8Array(5);
    data[0] = id;
    data[1] = turn > 0 ? 1 : 0;
    data[2] = Math.abs(turn);
    data[3] = Math.floor(drive/100);
    data[4] = drive%100;
    send(data);
}