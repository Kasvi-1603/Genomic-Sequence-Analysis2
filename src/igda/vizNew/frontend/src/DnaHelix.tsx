import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { palette, baseTint } from "./colors";

const PAIR_COUNT = 52;
const HELIX_HEIGHT = 14;
const HELIX_RADIUS = 1.1;
const TURNS = 3.2;

const matFront = {
  color: palette.strandFront,
  emissive: palette.strandFront,
  emissiveIntensity: 0.09,
  metalness: 0.5,
  roughness: 0.3,
};

const matBack = {
  color: palette.strandBack,
  emissive: palette.strandBack,
  emissiveIntensity: 0.05,
  metalness: 0.42,
  roughness: 0.42,
};

function helixPoint(t: number, strand: 0 | 1): THREE.Vector3 {
  const angle = t * TURNS * Math.PI * 2 + strand * Math.PI;
  const y = (t - 0.5) * HELIX_HEIGHT;
  return new THREE.Vector3(
    Math.cos(angle) * HELIX_RADIUS,
    y,
    Math.sin(angle) * HELIX_RADIUS
  );
}

function BaseNode({
  position,
  strand,
  phase,
  tintIndex,
}: {
  position: THREE.Vector3;
  strand: 0 | 1;
  phase: number;
  tintIndex: number;
}) {
  const mesh = useRef<THREE.Mesh>(null);
  const base = strand === 0 ? palette.strandFront : palette.strandBack;
  const tint = baseTint[tintIndex % 4];
  const color = useMemo(() => new THREE.Color(base).multiplyScalar(tint), [base, tint]);

  useFrame((state) => {
    if (!mesh.current) return;
    const t = state.clock.elapsedTime;
    const breathe = Math.sin(t * 0.55 + phase) * 0.012;
    mesh.current.position.set(position.x, position.y + breathe, position.z);
    mesh.current.rotation.y = Math.sin(t * 0.4 + phase) * 0.06;
  });

  return (
    <mesh ref={mesh} scale={strand === 0 ? 0.058 : 0.052}>
      <sphereGeometry args={[1, 18, 18]} />
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={strand === 0 ? 0.07 : 0.04}
        metalness={strand === 0 ? 0.45 : 0.38}
        roughness={strand === 0 ? 0.34 : 0.4}
      />
    </mesh>
  );
}

function Rung({
  start,
  end,
  phase,
}: {
  start: THREE.Vector3;
  end: THREE.Vector3;
  phase: number;
}) {
  const ref = useRef<THREE.Mesh>(null);
  const mid = useMemo(() => start.clone().add(end).multiplyScalar(0.5), [start, end]);
  const len = useMemo(() => start.distanceTo(end), [start, end]);
  const quat = useMemo(() => {
    const dir = end.clone().sub(start).normalize();
    const q = new THREE.Quaternion();
    q.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
    return q;
  }, [start, end]);

  useFrame((state) => {
    if (!ref.current) return;
    const t = state.clock.elapsedTime;
    ref.current.position.copy(mid);
    ref.current.position.y += Math.sin(t * 0.5 + phase) * 0.008;
    ref.current.quaternion.copy(quat);
    ref.current.scale.set(0.026, len * 0.5, 0.026);
  });

  return (
    <mesh ref={ref}>
      <cylinderGeometry args={[1, 1, 1, 12]} />
      <meshStandardMaterial
        color={palette.rung}
        emissive={palette.rung}
        emissiveIntensity={0.05}
        metalness={0.44}
        roughness={0.38}
      />
    </mesh>
  );
}

function StrandCurve({ strand }: { strand: 0 | 1 }) {
  const curve = useMemo(() => {
    const pts: THREE.Vector3[] = [];
    for (let i = 0; i <= 80; i++) {
      pts.push(helixPoint(i / 80, strand));
    }
    return new THREE.CatmullRomCurve3(pts);
  }, [strand]);

  return (
    <mesh renderOrder={strand === 0 ? 2 : 1}>
      <tubeGeometry args={[curve, 160, strand === 0 ? 0.023 : 0.02, 12, false]} />
      <meshStandardMaterial {...(strand === 0 ? matFront : matBack)} />
    </mesh>
  );
}

export function DnaHelix() {
  const group = useRef<THREE.Group>(null);

  const pairs = useMemo(
    () =>
      Array.from({ length: PAIR_COUNT }, (_, i) => ({
        phase: (i / PAIR_COUNT) * Math.PI * 2,
        tint: i % 4,
      })),
    []
  );

  const positions = useMemo(
    () =>
      pairs.map((_, i) => {
        const t = i / (PAIR_COUNT - 1);
        return { a: helixPoint(t, 0), b: helixPoint(t, 1) };
      }),
    [pairs]
  );

  useFrame((state, delta) => {
    if (!group.current) return;
    const t = state.clock.elapsedTime;
    group.current.rotation.y += delta * 0.028;
    group.current.position.y = Math.sin(t * 0.22) * 0.04;
  });

  return (
    <group
      ref={group}
      position={[-4.5, -5.8, 0]}
      rotation={[-0.22, 0.28, -0.72]}
      scale={1.18}
    >
      <StrandCurve strand={1} />
      <StrandCurve strand={0} />
      {positions.map((pos, i) => {
        const pair = pairs[i];
        return (
          <group key={i}>
            <Rung start={pos.a} end={pos.b} phase={pair.phase} />
            <BaseNode position={pos.a} strand={0} phase={pair.phase} tintIndex={pair.tint} />
            <BaseNode position={pos.b} strand={1} phase={pair.phase + 0.8} tintIndex={pair.tint} />
          </group>
        );
      })}
    </group>
  );
}
