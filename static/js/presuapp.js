// Función para crear gotas de lluvia de forma aleatoria
function createRaindrop() {
    const raindrop = document.createElement('div');
    raindrop.className = 'raindrop';
    raindrop.style.left = Math.random() * window.innerWidth + 'px';
    raindrop.style.top = Math.random() * window.innerHeight + 'px';
    document.querySelector('.rain').appendChild(raindrop);

    setTimeout(() => {
        raindrop.remove(); // Eliminar la gota después de un tiempo
    }, 3000); // Ajusta la duración de la gota
}

// Crear gotas de lluvia periódicamente
setInterval(createRaindrop, 100);

// Función para simular truenos
function simulateThunder() {
    const thunder = document.querySelector('.thunder');
    thunder.style.opacity = '1'; // Mostrar el trueno
    setTimeout(() => {
        thunder.style.opacity = '0'; // Ocultar el trueno después de un tiempo
    }, 200); // Ajusta la duración del trueno
}

// Llama a la función para simular truenos periódicamente
setInterval(simulateThunder, 5000); // Ajusta la frecuencia de los truenos
