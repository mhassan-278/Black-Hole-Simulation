
"""
Interactive 3D Schwarzschild black hole — real-time GR ray tracer.

Physics
-------
Null geodesics are integrated in Schwarzschild spacetime.  With the
Schwarzschild radius set to rs = 1 (so M = 1/2, G = c = 1) the orbit
equation for a photon is

        d2u/dphi2 + u = 3 M u2 ,      u = 1/r

which is reproduced in Cartesian form by the pseudo-Newtonian acceleration

        a  =  -3 M h2 x / r^5  =  -1.5 h2 x / r^5

where h = |x  x  v| is the conserved specific angular momentum of the ray.
This yields the correct photon sphere (r = 1.5), shadow, Einstein rings and
multiple images of the accretion disk.

Controls
--------
  Left mouse drag : orbit camera
  Mouse wheel     : zoom in / out
  SPACE           : toggle automatic camera orbit
  R               : reset view
  ESC / Q         : quit

"""

import math
import sys
import time

import numpy as np
import pygame
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader

# ============================================================================
#  CONFIGURATION
# ============================================================================
WIDTH, HEIGHT = 1280, 720
RENDER_SCALE  = 0.70     # internal render resolution (lower = faster)
DISK_INNER    = 3.0      # ISCO for Schwarzschild (r = 6M;  rs = 1 -> M = 0.5)
DISK_OUTER    = 14.0
DISK_BRIGHT   = 1.35

# ============================================================================
#  SHADERS
# ============================================================================
VERT_SRC = """
#version 330 core
layout(location = 0) in vec2 aPos;
out vec2 vUV;
void main(){
    vUV = aPos * 0.5 + 0.5;
    gl_Position = vec4(aPos, 0.0, 1.0);
}
"""

BH_FRAG_SRC = """
#version 330 core

out vec4 fragColor;

uniform vec2  uRes;
uniform vec3  uCamPos;
uniform vec3  uCamRight;
uniform vec3  uCamUp;
uniform vec3  uCamFwd;
uniform float uFov;
uniform float uTime;
uniform float uDiskInner;
uniform float uDiskOuter;
uniform float uDiskBright;

const int   MAX_STEPS = 300;
const float RS        = 1.0;    // Schwarzschild radius (unit of length)
const float ESCAPE_R  = 60.0;

// ---------------------------------------------------------------- hash
float hash13(vec3 p){
    p = fract(p * 0.1031);
    p += dot(p, p.yzx + 33.33);
    return fract((p.x + p.y) * p.z);
}

// ------------------------------------------------------------ star field
vec3 starField(vec3 dir){
    vec3 col = vec3(0.0);
    for (int k = 0; k < 3; ++k){
        float sc = 90.0 + 70.0 * float(k);
        vec3  p  = dir * sc;
        vec3  id = floor(p);
        vec3  f  = fract(p) - 0.5;
        float h  = hash13(id + float(k) * 57.13);
        if (h > 0.9625){
            float d2 = dot(f, f);
            float b  = (h - 0.9625) / 0.0375;
            float s  = smoothstep(0.055, 0.0, d2) * b;
            vec3  tint = mix(vec3(0.72, 0.82, 1.0),
                             vec3(1.00, 0.86, 0.68),
                             hash13(id + 7.31));
            col += tint * s * 2.2;
        }
    }
    // faint galactic band
    float band = exp(-pow(dir.y * 3.0, 2.0));
    col += vec3(0.035, 0.045, 0.075) * band;
    return col;
}

// ------------------------------------------------- accretion disk colour
vec3 diskColor(float r){
    float t = clamp((r - uDiskInner) / (uDiskOuter - uDiskInner), 0.0, 1.0);
    vec3 c = mix(vec3(1.00, 0.96, 0.90),
                 vec3(1.00, 0.55, 0.18), smoothstep(0.0, 0.45, t));
    c = mix(c, vec3(0.70, 0.16, 0.04), smoothstep(0.45, 1.0, t));
    return c;
}

// ================================================================= main
void main(){
    // ---- primary ray -----------------------------------------------------
    vec2  uv = (gl_FragCoord.xy - 0.5 * uRes) / uRes.y;
    float th = tan(uFov * 0.5);
    vec3  dir = normalize(uCamRight * (uv.x * 2.0 * th)
                        + uCamUp    * (uv.y * 2.0 * th)
                        + uCamFwd);

    vec3  pos = uCamPos;

    // conserved angular momentum of this ray
    vec3  Lv = cross(pos, dir);
    float h2 = dot(Lv, Lv);

    vec3  col   = vec3(0.0);
    float trans = 1.0;
    bool  captured = false;
    bool  escaped  = false;
    float prevY = pos.y;

    // ---- integrate the null geodesic ------------------------------------
    for (int i = 0; i < MAX_STEPS; ++i){
        float r2 = dot(pos, pos);
        float r  = sqrt(r2);

        if (r < RS * 1.0005) { captured = true; break; }          // horizon
        if (r > ESCAPE_R && dot(pos, dir) > 0.0) { escaped = true; break; }

        // adaptive step: fine near the hole, coarse far away
        float dt = clamp(0.07 * r, 0.02, 2.0);
        dt = min(dt, 0.4 * max(r - RS, 0.0) + 0.02);

        // gravitational acceleration  a = -1.5 h2 x / r^5
        float r5 = r2 * r2 * r;
        vec3  a  = -1.5 * h2 * pos / r5;

        // velocity-Verlet integration
        vec3  np  = pos + dir * dt + 0.5 * a * dt * dt;
        float nr2 = dot(np, np);
        float nr  = sqrt(nr2);
        vec3  a2  = -1.5 * h2 * np / (nr2 * nr2 * nr);
        vec3  nd  = dir + 0.5 * (a + a2) * dt;

        // ---- accretion disk crossing (equatorial plane y = 0) -----------
        if (prevY * np.y < 0.0){
            float f   = prevY / (prevY - np.y);
            vec3  hit = mix(pos, np, f);
            float hr  = length(hit.xz);

            if (hr > uDiskInner && hr < uDiskOuter){
                float t = (hr - uDiskInner) / (uDiskOuter - uDiskInner);

                float density = (0.25 + 0.75 * (1.0 - t)) * 0.62;
                density *= smoothstep(0.0, 0.06, t)
                         * (1.0 - smoothstep(0.55, 1.0, t));

                // rotating spiral structure
                float ang   = atan(hit.z, hit.x);
                float omega = 1.2 / pow(hr, 1.5);
                float n     = 0.5 + 0.5 * sin(6.0 * (ang + omega * uTime)
                                              + 4.0 * log(hr));
                density *= 0.65 + 0.70 * n;

                // --- relativistic Doppler beaming -------------------------
                vec3  vdir  = normalize(vec3(hit.z, 0.0, -hit.x));
                float speed = min(sqrt(0.5 / hr), 0.9);      // v = sqrt(M/r)
                vec3  beta  = vdir * speed;
                float gam   = 1.0 / sqrt(max(1.0 - dot(beta, beta), 1e-4));
                vec3  nObs  = -normalize(dir);               // source -> observer
                float dop   = 1.0 / (gam * max(1.0 - dot(beta, nObs), 1e-3));
                dop = clamp(dop, 0.2, 3.5);                  // beaming / redshift

                vec3 emit = diskColor(hr) * uDiskBright * pow(dop, 2.5);

                col   += trans * emit * density;
                trans *= (1.0 - clamp(density, 0.0, 1.0));
                if (trans < 0.01) break;
            }
        }

        pos   = np;
        dir   = nd;
        prevY = pos.y;
    }

    if (escaped) col += trans * starField(normalize(dir));

    // ---- tone mapping + gamma -------------------------------------------
    col = col / (1.0 + col);
    col = pow(max(col, vec3(0.0)), vec3(1.0 / 2.2));
    fragColor = vec4(col, 1.0);
}
"""

DISPLAY_FRAG_SRC = """
#version 330 core
in vec2 vUV;
out vec4 fragColor;
uniform sampler2D uTex;
void main(){
    fragColor = vec4(texture(uTex, vUV).rgb, 1.0);
}
"""

# ============================================================================
#  CAMERA
# ============================================================================
class Camera:
    def __init__(self):
        self.auto = True
        self.reset()

    def reset(self):
        self.dist  = 17.0
        self.yaw   = 0.6
        self.pitch = 0.18
        self.fov   = math.radians(52.0)

    def orbit(self, dyaw, dpitch):
        self.yaw   += dyaw
        self.pitch += dpitch
        self.pitch  = max(-1.50, min(1.50, self.pitch))

    def zoom(self, factor):
        self.dist = max(2.2, min(120.0, self.dist * factor))

    def basis(self):
        """Return (position, right, up, forward) as float tuples."""
        cp, sp = math.cos(self.pitch), math.sin(self.pitch)
        cy, sy = math.cos(self.yaw),   math.sin(self.yaw)

        pos = (self.dist * cp * sy,
               self.dist * sp,
               self.dist * cp * cy)

        fwd = (-cp * sy, -sp, -cp * cy)          # unit vector to origin
        world_up = (0.0, 1.0, 0.0)

        # right = normalize(cross(fwd, world_up))
        rx = fwd[1] * world_up[2] - fwd[2] * world_up[1]
        ry = fwd[2] * world_up[0] - fwd[0] * world_up[2]
        rz = fwd[0] * world_up[1] - fwd[1] * world_up[0]
        rl = math.sqrt(rx * rx + ry * ry + rz * rz)
        if rl < 1e-6:
            rx, ry, rz, rl = 1.0, 0.0, 0.0, 1.0
        right = (rx / rl, ry / rl, rz / rl)

        # up = cross(right, fwd)
        up = (right[1] * fwd[2] - right[2] * fwd[1],
              right[2] * fwd[0] - right[0] * fwd[2],
              right[0] * fwd[1] - right[1] * fwd[0])

        return pos, right, up, fwd

# ============================================================================
#  HELPERS
# ============================================================================
def gl_set_attr(name, value):
    try:
        pygame.display.gl_set_attribute(name, value)
    except Exception:
        pass


def create_fbo(w, h):
    tex = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, w, h, 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, None)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

    fbo = glGenFramebuffers(1)
    glBindFramebuffer(GL_FRAMEBUFFER, fbo)
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                           GL_TEXTURE_2D, tex, 0)
    if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
        raise RuntimeError("Framebuffer is not complete")
    glBindFramebuffer(GL_FRAMEBUFFER, 0)
    return fbo, tex


def delete_fbo(fbo, tex):
    glDeleteFramebuffers(1, [fbo])
    glDeleteTextures([tex])

# ============================================================================
#  MAIN
# ============================================================================
def main():
    pygame.init()

    gl_set_attr(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
    gl_set_attr(pygame.GL_CONTEXT_MINOR_VERSION, 3)
    gl_set_attr(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
    if hasattr(pygame, "GL_CONTEXT_FORWARD_COMPATIBLE_FLAG"):
        gl_set_attr(pygame.GL_CONTEXT_FORWARD_COMPATIBLE_FLAG, 1)
    gl_set_attr(pygame.GL_DEPTH_SIZE, 0)

    screen = pygame.display.set_mode(
        (WIDTH, HEIGHT),
        pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE)
    pygame.display.set_caption("Schwarzschild Black Hole - GR ray tracer")

    print(__doc__)
    print("OpenGL :", glGetString(GL_VERSION).decode())
    print("GPU    :", glGetString(GL_RENDERER).decode())

    # ------------------------------------------------------------- programs
    bh_prog = compileProgram(
        compileShader(VERT_SRC, GL_VERTEX_SHADER),
        compileShader(BH_FRAG_SRC, GL_FRAGMENT_SHADER))

    disp_prog = compileProgram(
        compileShader(VERT_SRC, GL_VERTEX_SHADER),
        compileShader(DISPLAY_FRAG_SRC, GL_FRAGMENT_SHADER))

    bh_u = {n: glGetUniformLocation(bh_prog, n) for n in (
        "uRes", "uCamPos", "uCamRight", "uCamUp", "uCamFwd",
        "uFov", "uTime", "uDiskInner", "uDiskOuter", "uDiskBright")}
    disp_u_tex = glGetUniformLocation(disp_prog, "uTex")

    # ---------------------------------------------------------- fullscreen quad
    verts = np.array([-1, -1, 1, -1, -1, 1, 1, 1], dtype=np.float32)
    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)
    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_STATIC_DRAW)
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, None)
    glBindVertexArray(0)

    glDisable(GL_DEPTH_TEST)

    # ------------------------------------------------------------------ state
    cam = Camera()
    win_w, win_h = screen.get_size()
    rw = max(1, int(win_w * RENDER_SCALE))
    rh = max(1, int(win_h * RENDER_SCALE))
    fbo, fbo_tex = create_fbo(rw, rh)

    clock = pygame.time.Clock()
    t0 = time.time()
    running = True
    dragging = False
    fps_smooth = 0.0

    while running:
        dt = clock.tick(120) / 1000.0
        dt = min(dt, 0.1)

        # ------------------------------------------------------------- events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_r:
                    cam.reset()
                elif event.key == pygame.K_SPACE:
                    cam.auto = not cam.auto

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    dragging = True
                    pygame.mouse.get_rel()
                elif event.button == 4:
                    cam.zoom(0.92)
                elif event.button == 5:
                    cam.zoom(1.08)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    dragging = False

            elif event.type == pygame.MOUSEWHEEL:
                cam.zoom(math.exp(-event.y * 0.10))

            elif event.type == pygame.VIDEORESIZE:
                win_w, win_h = max(320, event.w), max(240, event.h)
                screen = pygame.display.set_mode(
                    (win_w, win_h),
                    pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE)
                delete_fbo(fbo, fbo_tex)
                rw = max(1, int(win_w * RENDER_SCALE))
                rh = max(1, int(win_h * RENDER_SCALE))
                fbo, fbo_tex = create_fbo(rw, rh)

        # ------------------------------------------------------------- input
        if dragging:
            mx, my = pygame.mouse.get_rel()
            cam.orbit(-mx * 0.005, my * 0.005)
        else:
            pygame.mouse.get_rel()

        if cam.auto and not dragging:
            cam.orbit(dt * 0.10, 0.0)

        # --------------------------------------------------------- render BH
        pos, right, up, fwd = cam.basis()
        t = time.time() - t0

        glBindFramebuffer(GL_FRAMEBUFFER, fbo)
        glViewport(0, 0, rw, rh)
        glUseProgram(bh_prog)
        glUniform2f(bh_u["uRes"], float(rw), float(rh))
        glUniform3f(bh_u["uCamPos"],   *pos)
        glUniform3f(bh_u["uCamRight"], *right)
        glUniform3f(bh_u["uCamUp"],    *up)
        glUniform3f(bh_u["uCamFwd"],   *fwd)
        glUniform1f(bh_u["uFov"],         cam.fov)
        glUniform1f(bh_u["uTime"],        t)
        glUniform1f(bh_u["uDiskInner"],   DISK_INNER)
        glUniform1f(bh_u["uDiskOuter"],   DISK_OUTER)
        glUniform1f(bh_u["uDiskBright"],  DISK_BRIGHT)

        glBindVertexArray(vao)
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

        # ------------------------------------------------------ blit to screen
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glViewport(0, 0, win_w, win_h)
        glUseProgram(disp_prog)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, fbo_tex)
        glUniform1i(disp_u_tex, 0)
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

        pygame.display.flip()

        # ------------------------------------------------------------- title
        fps = clock.get_fps()
        fps_smooth = fps if fps_smooth == 0.0 else fps_smooth * 0.9 + fps * 0.1
        pygame.display.set_caption(
            f"Schwarzschild Black Hole  |  {fps_smooth:5.1f} FPS  |  "
            f"render {rw}x{rh}  |  r = {cam.dist:5.1f} rs  |  "
            f"[drag] orbit  [wheel] zoom  [space] auto  [R] reset  [ESC] quit")

    delete_fbo(fbo, fbo_tex)
    pygame.quit()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:            # noqa: BLE001
        pygame.quit()
        print("\n[ERROR]", exc)
        print("Make sure you have an OpenGL 3.3 capable GPU/driver and that "
              "pygame, PyOpenGL and numpy are installed.")
        sys.exit(1)