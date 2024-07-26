import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSG } from 'https://cdn.jsdelivr.net/gh/Sean-Bradley/THREE-CSGMesh@master/dist/client/CSGMesh.js';

let scene, camera, renderer, controls;
let countertop, sink, holeMesh;

function init3D() {
    // Escena
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth * 0.6, 500); // Ajustar el tamaño del canvas
    document.getElementById('3d-container').appendChild(renderer.domElement);

    // Controles de órbita
    controls = new OrbitControls(camera, renderer.domElement);

    // Luz
    const light = new THREE.DirectionalLight(0xffffff, 1);
    light.position.set(5, 5, 5).normalize();
    scene.add(light);

    // Encimera (cubo simple como ejemplo)
    const geometry = new THREE.BoxGeometry(1, 0.1, 1);
    const material = new THREE.MeshPhongMaterial({ color: 0xffffff });
    countertop = new THREE.Mesh(geometry, material);

    // Crear agujero en la encimera usando THREE-CSGMesh
    const sinkHoleGeometry = new THREE.BoxGeometry(0.3, 0.1, 0.3);
    holeMesh = new THREE.Mesh(sinkHoleGeometry);
    holeMesh.position.set(0, 0, 0);

    const countertopCSG = CSG.fromMesh(countertop);
    const sinkHoleCSG = CSG.fromMesh(holeMesh);
    const resultCSG = countertopCSG.subtract(sinkHoleCSG);
    const result = CSG.toMesh(resultCSG, countertop.matrix);
    result.material = material;

    // Fregadero (cubo pequeño como ejemplo)
    const sinkGeometry = new THREE.BoxGeometry(0.3, 0.1, 0.3);
    const sinkMaterial = new THREE.MeshPhongMaterial({ color: 0xffffff });
    sink = new THREE.Mesh(sinkGeometry, sinkMaterial);
    sink.position.y = -0.1; // Posicionar el fregadero justo debajo de la encimera

    scene.add(result);
    scene.add(sink);

    camera.position.z = 2;
    controls.update();

    window.addEventListener('keydown', onDocumentKeyDown, false);

    animate();
}

function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}

function update3DModel() {
    // Asegúrate de que el modelo 3D está inicializado
    if (!countertop || !sink) return;

    // Obtener valores seleccionados
    const length = document.getElementById('length').value;
    const width = document.getElementById('width').value;
    const color = document.getElementById('color').value;
    const sinkType = document.getElementById('sinkType').value;

    // Actualizar dimensiones
    countertop.scale.x = length / 100 || 1;
    countertop.scale.z = width / 100 || 1;

    // Actualizar color de la encimera
    if (color === 'rojo') {
        countertop.material.color.set(0xff0000);
    } else if (color === 'azul') {
        countertop.material.color.set(0x0000ff);
    } else if (color === 'blanco') {
        countertop.material.color.set(0xffffff);
    }

    // Actualizar fregadero
    if (sinkType === 'solid') {
        sink.material.color.set(countertop.material.color.getHex()); // Mismo color que la encimera
    } else if (sinkType === 'steel') {
        sink.material.color.set(0xaaaaaa); // Color de acero
    }

    // Reposicionar el fregadero dentro del agujero
    sink.position.x = (length / 200) - 0.15;
    sink.position.z = (width / 200) - 0.15;

    // Actualizar el hueco
    updateSinkHole();
}

function updateSinkHole() {
    const countertopCSG = CSG.fromMesh(countertop);
    const sinkHoleCSG = CSG.fromMesh(holeMesh);
    const resultCSG = countertopCSG.subtract(sinkHoleCSG);
    const result = CSG.toMesh(resultCSG, countertop.matrix);
    result.material = countertop.material;

    // Eliminar el antiguo mesh y agregar el nuevo
    scene.remove(countertop);
    countertop = result;
    scene.add(countertop);
}

function onDocumentKeyDown(event) {
    const step = 0.01;
    switch (event.key) {
        case 'ArrowUp':
            moveSink(0, -step);
            break;
        case 'ArrowDown':
            moveSink(0, step);
            break;
        case 'ArrowLeft':
            moveSink(-step, 0);
            break;
        case 'ArrowRight':
            moveSink(step, 0);
            break;
    }
}

function moveSink(deltaX, deltaZ) {
    sink.position.x += deltaX;
    sink.position.z += deltaZ;
    holeMesh.position.x += deltaX;
    holeMesh.position.z += deltaZ;

    // Limitar el movimiento del fregadero a la superficie de la encimera
    let halfLength = (document.getElementById('length').value / 200) - 0.15;
    let halfWidth = (document.getElementById('width').value / 200) - 0.15;
    sink.position.x = Math.max(-halfLength, Math.min(halfLength, sink.position.x));
    sink.position.z = Math.max(-halfWidth, Math.min(halfWidth, sink.position.z));
    holeMesh.position.x = Math.max(-halfLength, Math.min(halfLength, holeMesh.position.x));
    holeMesh.position.z = Math.max(-halfWidth, Math.min(halfWidth, holeMesh.position.z));

    // Actualizar el agujero en la encimera
    updateSinkHole();
}

window.onload = init3D;
