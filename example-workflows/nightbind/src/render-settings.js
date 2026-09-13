import * as THREE from "three";

// Shared by the game and the actual-GLB inspection route.
export const LOOK = Object.freeze({
  background: 0x101c23,
  fogDensity: 0.014,
  exposure: 1.3,
  camera: [0, 36, 28],
  halfHeight: 18,
  narrowHalfHeight: 22,
});
const origin = new THREE.Vector3();
const gameOffset = new THREE.Vector3(...LOOK.camera);
const portraitOffset = new THREE.Vector3(25, 30, 34);

export function createRenderer(
  container,
  { dpr = Math.min(devicePixelRatio, 1.5), label = "Nightbind scene" } = {},
) {
  const renderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: false,
    powerPreference: "high-performance",
  });
  renderer.setPixelRatio(dpr);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = LOOK.exposure;
  renderer.domElement.setAttribute("aria-label", label);
  renderer.domElement.tabIndex = 0;
  container.append(renderer.domElement);
  return renderer;
}
export function createLitScene() {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(LOOK.background);
  scene.fog = new THREE.FogExp2(LOOK.background, LOOK.fogDensity);
  scene.add(new THREE.HemisphereLight(0xc4e5ed, 0x3f3c37, 2));
  for (const [color, intensity, position] of [
    [0xffdba5, 3, [-14, 24, 9]],
    [0x729fdb, 2, [10, 12, -18]],
  ]) {
    const light = new THREE.DirectionalLight(color, intensity);
    light.position.set(...position);
    scene.add(light);
  }
  return scene;
}
export function createGameCamera() {
  const camera = new THREE.OrthographicCamera(-32, 32, 18, -18, 0.1, 110);
  camera.position.set(...LOOK.camera);
  camera.lookAt(0, 0, 0);
  return camera;
}
export function fitGameCamera(
  camera,
  width,
  height,
  {
    halfHeight = width / height < 1.3 ? LOOK.narrowHalfHeight : LOOK.halfHeight,
    target = origin,
    portrait = false,
  } = {},
) {
  const aspect = width / height;
  camera.left = -halfHeight * aspect;
  camera.right = halfHeight * aspect;
  camera.top = halfHeight;
  camera.bottom = -halfHeight;
  camera.position.copy(target).add(portrait ? portraitOffset : gameOffset);
  camera.lookAt(target);
  camera.updateProjectionMatrix();
}
export function graphicsBackend(renderer) {
  const gl = renderer.getContext(),
    ext = gl.getExtension("WEBGL_debug_renderer_info");
  return ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : "unavailable";
}
