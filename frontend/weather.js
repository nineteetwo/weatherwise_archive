const canvas = document.getElementById('weather-canvas');
const ctx = canvas.getContext('2d');

let particles = [];
let currentWeather = 'clear'; 

function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
}
window.addEventListener('resize', resizeCanvas);
resizeCanvas();

class Particle {
    constructor(type) {
        this.type = type;
        this.reset();
    }

    reset() {
        this.x = Math.random() * canvas.width;
        this.y = Math.random() * -canvas.height;
        
        if (this.type === 'snow') {
            this.size = Math.random() * 3 + 1;
            this.speedY = Math.random() * 1 + 0.5;
            this.speedX = (Math.random() - 0.5) * 1;
            this.opacity = Math.random() * 0.5 + 0.3;
        } else {
            this.size = Math.random() * 1.5 + 0.5;
            this.speedY = Math.random() * 10 + 10;
            this.speedX = Math.random() * 2 - 1;
            this.length = Math.random() * 20 + 10;
            this.opacity = Math.random() * 0.3 + 0.2;
        }
    }

    update() {
        this.y += this.speedY;
        this.x += this.speedX;

        if (this.y > canvas.height) {
            this.reset();
            this.y = 0; 
        }
    }

    draw() {
        ctx.globalAlpha = this.opacity;
        if (this.type === 'snow') {
            ctx.fillStyle = '#ffffff';
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fill();
        } else {
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = this.size;
            ctx.beginPath();
            ctx.moveTo(this.x, this.y);
            ctx.lineTo(this.x + this.speedX, this.y + this.length);
            ctx.stroke();
        }
        ctx.globalAlpha = 1; 
    }
}

function initParticles() {
    particles = [];
    let count = 0;
    let type = 'rain';

    if (currentWeather === 'rain') { count = 150; type = 'rain'; }
    if (currentWeather === 'heavy-rain' || currentWeather === 'thunder') { count = 400; type = 'rain'; }
    if (currentWeather === 'snow') { count = 200; type = 'snow'; }

    for (let i = 0; i < count; i++) {
        particles.push(new Particle(type));
    }
}

function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    particles.forEach(p => {
        p.update();
        p.draw();
    });

    requestAnimationFrame(animate);
}

window.setWeatherEffect = function(weatherType) {
    currentWeather = weatherType;
    initParticles();
};

animate();