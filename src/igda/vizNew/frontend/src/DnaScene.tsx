import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { PerspectiveCamera } from "@react-three/drei";
import { EffectComposer, Bloom } from "@react-three/postprocessing";
import { DnaHelix } from "./DnaHelix";
import { palette } from "./colors";

const BG = 0x100d20;
const LIGHT_ROSE = 0xfda1a2;
const LIGHT_AMBIENT = 0x1d1842;

/** Soft separation glow behind the helix — not part of the geometry */
function HelixBackdrop() {
  return (
    <mesh position={[-1.2, 0.2, -4.5]} renderOrder={-1}>
      <planeGeometry args={[14, 18]} />
      <meshBasicMaterial
        color={palette.glow}
        transparent
        opacity={0.055}
        depthWrite={false}
        toneMapped={false}
      />
    </mesh>
  );
}

function SceneContent() {
  return (
    <>
      <color attach="background" args={[BG]} />
      <PerspectiveCamera
        makeDefault
        position={[7.8, -1.4, 9.2]}
        fov={38}
        near={0.1}
        far={80}
        onUpdate={(self) => self.lookAt(-2, 1.2, 0)}
      />

      <ambientLight color={LIGHT_AMBIENT} intensity={0.88} />
      <pointLight
        color={LIGHT_ROSE}
        intensity={1.85}
        distance={300}
        decay={2}
        position={[3, 7, 7.5]}
      />
      {/* Subtle backlight — separates helix from background */}
      <pointLight
        color={LIGHT_ROSE}
        intensity={0.65}
        distance={45}
        decay={2}
        position={[-3.5, 1.5, -5]}
      />
      <pointLight
        color={0x8e0d3c}
        intensity={0.35}
        distance={35}
        decay={2}
        position={[-4, -3, -4]}
      />

      <HelixBackdrop />
      <DnaHelix />

      <EffectComposer multisampling={0}>
        <Bloom
          luminanceThreshold={0.68}
          luminanceSmoothing={0.35}
          intensity={0.32}
          mipmapBlur
        />
      </EffectComposer>
    </>
  );
}

export function DnaScene() {
  return (
    <Canvas
      dpr={[1, 1.75]}
      gl={{
        antialias: true,
        alpha: false,
        powerPreference: "high-performance",
      }}
      style={{ width: "100%", height: "100%", display: "block" }}
    >
      <Suspense fallback={null}>
        <SceneContent />
      </Suspense>
    </Canvas>
  );
}
