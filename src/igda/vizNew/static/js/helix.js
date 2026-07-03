/**
 * IGDA home DNA double helix — cinematic crop: structure flows through panel,
 * continues off-screen lower-left → upper-right (not boxed inside frame).
 */
(function () {
  function init() {
    const canvas = document.getElementById("dna-helix");
    if (!canvas) return;
    if (typeof THREE === "undefined") {
      console.error("[helix] THREE is not loaded — check CDN script order.");
      return;
    }

    const container = canvas.parentElement;
    if (!container) return;

    const BG = 0x100d20;
    const ROSE = 0xfda1a2;
    const TEAL = 0x1d9e75;
    const TEAL_STRAND = 0x28b088;
    const AMBIENT = 0x1d1842;
    const RUNG = 0xe2e0f0;

    const HELIX_RADIUS = 1.05;
    const HELIX_HEIGHT = 21;
    const TURNS = 5;
    const POINTS_PER_TURN = 24;
    const TOTAL_POINTS = TURNS * POINTS_PER_TURN;
    const TUBE_SEGMENTS = TOTAL_POINTS * 2;
    const STRAND_TUBE_RADIUS = 0.074;
    const RUNG_TUBE_RADIUS = 0.04;
    const SPHERE_RADIUS = 0.115;
    const RUNG_EVERY = 3;
    const ROTATION_SPEED = 0.004;

    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: false,
      powerPreference: "high-performance",
    });
    renderer.setClearColor(BG, 1);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(BG);
    scene.fog = new THREE.Fog(BG, 28, 65);

    const camera = new THREE.PerspectiveCamera(48, 1, 0.1, 150);
    const lookTarget = new THREE.Vector3(0.1, 2.05, 0);

    scene.add(new THREE.AmbientLight(AMBIENT, 0.95));

    const pinkLight = new THREE.PointLight(ROSE, 2.2, 120);
    pinkLight.position.set(4, 9, 9);
    scene.add(pinkLight);

    const tealLight = new THREE.PointLight(TEAL, 1.1, 90);
    tealLight.position.set(-4, -6, 7);
    scene.add(tealLight);

    const backLight = new THREE.PointLight(ROSE, 0.55, 70);
    backLight.position.set(-6, 3, -7);
    scene.add(backLight);

    const mat1 = new THREE.MeshStandardMaterial({
      color: ROSE,
      emissive: ROSE,
      emissiveIntensity: 0.08,
      roughness: 0.28,
      metalness: 0.48,
    });

    const mat2 = new THREE.MeshStandardMaterial({
      color: TEAL_STRAND,
      emissive: TEAL_STRAND,
      emissiveIntensity: 0.09,
      roughness: 0.3,
      metalness: 0.42,
    });

    const matRung = new THREE.MeshStandardMaterial({
      color: RUNG,
      roughness: 0.5,
      metalness: 0.15,
      transparent: true,
      opacity: 0.62,
    });

    function buildStrandPoints(phaseOffset) {
      const pts = [];
      for (let i = 0; i <= TOTAL_POINTS; i++) {
        const t = i / TOTAL_POINTS;
        const angle = t * TURNS * Math.PI * 2 + phaseOffset;
        const y = (t - 0.5) * HELIX_HEIGHT;
        pts.push(
          new THREE.Vector3(
            Math.cos(angle) * HELIX_RADIUS,
            y,
            Math.sin(angle) * HELIX_RADIUS
          )
        );
      }
      return pts;
    }

    const pts1 = buildStrandPoints(0);
    const pts2 = buildStrandPoints(Math.PI);

    function makeTube(points, material) {
      const curve = new THREE.CatmullRomCurve3(points);
      const geo = new THREE.TubeGeometry(
        curve,
        TUBE_SEGMENTS,
        STRAND_TUBE_RADIUS,
        10,
        false
      );
      return new THREE.Mesh(geo, material);
    }

    /** Fixed diagonal anchor — lower-left → upper-right, never animated */
    const anchorGroup = new THREE.Group();
    anchorGroup.rotation.order = "YXZ";
    anchorGroup.rotation.set(-0.15, 0.44, -0.84);
    anchorGroup.position.set(-5.4, -2.85, 0.2);
    anchorGroup.scale.setScalar(1.59);
    scene.add(anchorGroup);

    const spinGroup = new THREE.Group();
    anchorGroup.add(spinGroup);

    spinGroup.add(makeTube(pts1, mat1));
    spinGroup.add(makeTube(pts2, mat2));

    const sphereGeo = new THREE.SphereGeometry(SPHERE_RADIUS, 12, 12);
    const phaseStep = (Math.PI * 2) / TOTAL_POINTS;

    function addSpheres(points, material, phaseBase) {
      points.forEach((pt, i) => {
        if (i % 2 !== 0) return;
        const mesh = new THREE.Mesh(sphereGeo, material);
        mesh.position.copy(pt);
        mesh.userData.phase = phaseBase + i * phaseStep;
        mesh.userData.baseY = pt.y;
        spinGroup.add(mesh);
      });
    }

    addSpheres(pts1, mat1, 0);
    addSpheres(pts2, mat2, Math.PI);

    for (let i = 0; i < pts1.length; i += RUNG_EVERY) {
      const a = pts1[i];
      const b = pts2[i];
      const dir = new THREE.Vector3().subVectors(b, a);
      const len = dir.length();
      if (len < 1e-6) continue;
      const mid = new THREE.Vector3().addVectors(a, b).multiplyScalar(0.5);
      const rungGeo = new THREE.CylinderGeometry(
        RUNG_TUBE_RADIUS,
        RUNG_TUBE_RADIUS,
        len,
        8
      );
      const rung = new THREE.Mesh(rungGeo, matRung);
      rung.position.copy(mid);
      rung.quaternion.setFromUnitVectors(
        new THREE.Vector3(0, 1, 0),
        dir.normalize()
      );
      rung.userData.phase = i * phaseStep;
      rung.userData.baseY = mid.y;
      spinGroup.add(rung);
    }

    /**
     * Cinematic crop — camera stays close; helix is larger than the frame.
     * Do NOT fit the full bounding box (that makes it look contained).
     */
    function updateCamera() {
      const aspect = Math.max(container.clientWidth, 1) / Math.max(container.clientHeight, 1);
      const wide = aspect > 1.15;

      camera.position.set(
        wide ? 3.6 : 3.2,
        wide ? 0.4 : 0.55,
        wide ? 5.4 : 5.9
      );
      camera.lookAt(lookTarget);
      camera.updateProjectionMatrix();
    }

    const clock = new THREE.Clock();

    function resize() {
      const w = Math.max(container.clientWidth, 1);
      const h = Math.max(container.clientHeight, 1);
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      updateCamera();
    }

    resize();
    window.addEventListener("resize", resize);

    let frameId = 0;
    function animate() {
      frameId = requestAnimationFrame(animate);
      const t = clock.getElapsedTime();
      spinGroup.rotation.y += ROTATION_SPEED;

      spinGroup.children.forEach((child) => {
        if (child.userData.phase === undefined) return;
        const breathe = Math.sin(t * 0.55 + child.userData.phase) * 0.01;
        if (child.userData.baseY !== undefined) {
          child.position.y = child.userData.baseY + breathe;
        }
      });

      renderer.render(scene, camera);
    }

    animate();

    window.addEventListener("beforeunload", () => {
      cancelAnimationFrame(frameId);
      renderer.dispose();
      sphereGeo.dispose();
      [mat1, mat2, matRung].forEach((m) => m.dispose());
      spinGroup.traverse((obj) => {
        if (obj.geometry) obj.geometry.dispose();
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
