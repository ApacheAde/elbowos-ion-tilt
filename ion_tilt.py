#!/usr/bin/env python3
"""ION TILT — neon pinball arcade for ElbowOS. Python 3 + pygame."""
import math, os, random, subprocess, sys

RECORD = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
PLAY = "--play" in sys.argv
if RECORD or not PLAY:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

W, H, FPS, SECS = 1080, 1920, 30, 15
OUT = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/ION_TILT_ElbowOS.mp4")
TITLE, HANDLE = "ION TILT", "x.com/ElbowOS"

VOID = (8, 4, 18)
PLANK = (22, 10, 42)
GOLD = (255, 196, 48)
AMBER = (255, 148, 32)
PINK = (255, 48, 168)
VIO = (168, 72, 255)
CYAN = (72, 236, 255)
WHITE = (250, 246, 255)
LIME = (140, 255, 80)
INK = (14, 8, 28)

L, R, TOP, BOT = 90, W - 90, 210, 1760
FL_Y, FL_LEN, FL_W = 1588, 168, 18
BR = 18


class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        flags = 0 if PLAY else pygame.HIDDEN
        try:
            self.screen = pygame.display.set_mode((W, H), flags)
        except pygame.error:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            pygame.display.quit()
            pygame.display.init()
            self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption(TITLE)
        self.font_lg = pygame.font.SysFont("DejaVu Sans", 64, bold=True)
        self.font = pygame.font.SysFont("DejaVu Sans", 40, bold=True)
        self.font_sm = pygame.font.SysFont("DejaVu Sans", 26)
        self.clock = pygame.time.Clock()
        self.score = self.combo = self.t = self.flash = self.balls = 0
        self.la = self.ra = 0.42
        self.lf = self.rf = False
        self.bumpers = [[280, 620, 54, VIO, 0], [800, 620, 54, PINK, 0], [540, 420, 62, CYAN, 0]]
        self.spinners = [[300, 980], [780, 980]]
        self.spin = [0.0, 0.0]
        self.sparks, self.rings = [], []
        self.stars = [[random.randint(0, W), random.randint(0, H), random.uniform(0.2, 1.4),
                       random.choice([VIO, PINK, GOLD, CYAN])] for _ in range(70)]
        self.ball = None
        self.cooldown = 10
        self.banner = 0
        self.spawn()

    def spawn(self):
        self.ball = [R - 70, BOT - 80, random.uniform(-2.4, -0.6), -18.5]
        self.balls += 1
        self.cooldown = 12
        self.burst(self.ball[0], self.ball[1], GOLD, 10)

    def burst(self, x, y, col, n=12):
        for _ in range(n):
            a = random.uniform(0, 6.2832)
            sp = random.uniform(2, 10)
            self.sparks.append([x, y, math.cos(a) * sp, math.sin(a) * sp, 16, col])

    def hinge(self, left):
        return (L + 88, FL_Y) if left else (R - 88, FL_Y)

    def flip_pts(self, left, ang):
        hx, hy = self.hinge(left)
        a = math.pi - ang if left else ang
        ex = hx + math.cos(a) * FL_LEN
        ey = hy + math.sin(a) * FL_LEN
        return hx, hy, ex, ey

    def bounce_seg(self, x, y, vx, vy, x1, y1, x2, y2, kick=0.0):
        dx, dy = x2 - x1, y2 - y1
        ln = math.hypot(dx, dy) or 1
        px, py = x - x1, y - y1
        t = max(0.0, min(1.0, (px * dx + py * dy) / (ln * ln)))
        cx, cy = x1 + t * dx, y1 + t * dy
        nx, ny = x - cx, y - cy
        d = math.hypot(nx, ny) or 1
        if d >= BR + FL_W:
            return x, y, vx, vy, False
        nx, ny = nx / d, ny / d
        x = cx + nx * (BR + FL_W + 1)
        y = cy + ny * (BR + FL_W + 1)
        vn = vx * nx + vy * ny
        vx = (vx - 2.1 * vn * nx) * 0.92 + nx * kick
        vy = (vy - 2.1 * vn * ny) * 0.92 + ny * kick
        return x, y, vx, vy, True

    def autoplay(self):
        if not self.ball:
            return
        x, y, vx, vy = self.ball
        want_l = y > 1280 and x < W * 0.58 and vy > -2
        want_r = y > 1280 and x > W * 0.42 and vy > -2
        if want_l and not self.lf:
            self.lf = True
        if want_r and not self.rf:
            self.rf = True
        if y < 1100 or vy < -6:
            self.lf = self.rf = False
        if y > 1680 and abs(x - W / 2) < 90:
            self.lf = self.rf = True

    def tick(self):
        self.t += 1
        self.flash = max(0, self.flash - 1)
        self.banner = max(0, self.banner - 1)
        self.cooldown = max(0, self.cooldown - 1)
        tgt = 0.08 if self.lf else 0.62
        self.la += (tgt - self.la) * 0.42
        tgt = 0.08 if self.rf else 0.62
        self.ra += (tgt - self.ra) * 0.42
        for i, s in enumerate(self.spin):
            self.spin[i] = s + 0.18 + 0.08 * math.sin(self.t * 0.07 + i)
        if self.ball:
            x, y, vx, vy = self.ball
            vy += 0.42
            vx *= 0.999
            vy *= 0.999
            x += vx
            y += vy
            if x < L + BR:
                x, vx = L + BR, abs(vx) * 0.86
            if x > R - BR:
                x, vx = R - BR, -abs(vx) * 0.86
            if y < TOP + BR:
                y, vy = TOP + BR, abs(vy) * 0.8
            for b in self.bumpers:
                dx, dy = x - b[0], y - b[1]
                d = math.hypot(dx, dy) or 1
                lim = b[2] + BR
                if d < lim:
                    nx, ny = dx / d, dy / d
                    x, y = b[0] + nx * (lim + 2), b[1] + ny * (lim + 2)
                    spd = max(11.0, math.hypot(vx, vy) * 0.35 + 13)
                    vx, vy = nx * spd, ny * spd
                    b[4] = 10
                    self.combo += 1
                    self.score += 40 + self.combo * 6
                    self.flash = 6
                    self.burst(b[0], b[1], b[3], 16)
                    self.rings.append([b[0], b[1], 8, b[3]])
                    self.banner = 12
            for i, (sx, sy) in enumerate(self.spinners):
                if math.hypot(x - sx, y - sy) < 46:
                    self.spin[i] += 0.9
                    self.score += 8
                    vx *= 1.04
                    vy *= 1.04
            kick_l = 16 if self.lf and self.la < 0.28 else 3
            kick_r = 16 if self.rf and self.ra < 0.28 else 3
            hx, hy, ex, ey = self.flip_pts(True, self.la)
            x, y, vx, vy, hit = self.bounce_seg(x, y, vx, vy, hx, hy, ex, ey, kick_l)
            if hit:
                self.score += 5
                self.burst(x, y, GOLD, 6)
            hx, hy, ex, ey = self.flip_pts(False, self.ra)
            x, y, vx, vy, hit = self.bounce_seg(x, y, vx, vy, hx, hy, ex, ey, kick_r)
            if hit:
                self.score += 5
                self.burst(x, y, GOLD, 6)
            for ax, ay, bx, by in ((L, 1320, L + 160, 1480), (R, 1320, R - 160, 1480)):
                x, y, vx, vy, hit = self.bounce_seg(x, y, vx, vy, ax, ay, bx, by, 9)
                if hit:
                    self.score += 12
                    self.burst(x, y, PINK, 8)
            if y > BOT + 40:
                self.combo = 0
                self.burst(x, y, PINK, 14)
                self.ball = None
                self.cooldown = 18
            else:
                self.ball = [x, y, vx, vy]
        if self.ball is None and self.cooldown <= 0:
            self.spawn()
        for p in self.sparks:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += 0.16
            p[4] -= 1
        self.sparks = [p for p in self.sparks if p[4] > 0]
        for r in self.rings:
            r[2] += 7
        self.rings = [r for r in self.rings if r[2] < 160]
        for b in self.bumpers:
            b[4] = max(0, b[4] - 1)
        for e in self.stars:
            e[1] -= e[2]
            if e[1] < -6:
                e[1] = H + 6
                e[0] = random.randint(0, W)

    def draw(self, surf):
        surf.fill(VOID)
        for e in self.stars:
            pygame.draw.circle(surf, e[3], (int(e[0]), int(e[1])), 2)
        pygame.draw.rect(surf, PLANK, (L - 18, TOP - 18, R - L + 36, BOT - TOP + 36), border_radius=36)
        pygame.draw.rect(surf, INK, (L, TOP, R - L, BOT - TOP), border_radius=28)
        pygame.draw.rect(surf, VIO, (L, TOP, R - L, BOT - TOP), 3, border_radius=28)
        pygame.draw.line(surf, GOLD, (L + 40, TOP + 70), (R - 40, TOP + 70), 3)
        pygame.draw.polygon(surf, (48, 16, 64), [(L, 1320), (L, 1500), (L + 160, 1480)])
        pygame.draw.polygon(surf, (48, 16, 64), [(R, 1320), (R, 1500), (R - 160, 1480)])
        pygame.draw.line(surf, PINK, (L, 1320), (L + 160, 1480), 5)
        pygame.draw.line(surf, PINK, (R, 1320), (R - 160, 1480), 5)
        pygame.draw.rect(surf, (36, 8, 28), (W // 2 - 70, BOT - 20, 140, 50), border_radius=8)
        for i, (sx, sy) in enumerate(self.spinners):
            a = self.spin[i]
            pygame.draw.circle(surf, GOLD, (sx, sy), 28, 3)
            pygame.draw.line(surf, AMBER, (sx + math.cos(a) * 22, sy + math.sin(a) * 22),
                             (sx - math.cos(a) * 22, sy - math.sin(a) * 22), 4)
        for b in self.bumpers:
            rad = b[2] + (6 if b[4] else 0)
            pygame.draw.circle(surf, b[3], (b[0], b[1]), rad)
            pygame.draw.circle(surf, WHITE, (b[0], b[1]), rad, 3)
            pygame.draw.circle(surf, INK, (b[0], b[1]), rad // 3)
        for left, ang, col in ((True, self.la, CYAN), (False, self.ra, LIME)):
            hx, hy, ex, ey = self.flip_pts(left, ang)
            pygame.draw.line(surf, col, (hx, hy), (ex, ey), 16)
            pygame.draw.circle(surf, WHITE, (int(hx), int(hy)), 12)
            pygame.draw.circle(surf, GOLD, (int(ex), int(ey)), 8)
        if self.ball:
            bx, by = int(self.ball[0]), int(self.ball[1])
            pygame.draw.circle(surf, GOLD, (bx, by), BR)
            pygame.draw.circle(surf, WHITE, (bx - 5, by - 6), 6)
            pygame.draw.circle(surf, AMBER, (bx, by), BR, 2)
        for r in self.rings:
            pygame.draw.circle(surf, r[3], (int(r[0]), int(r[1])), int(r[2]), 3)
        for p in self.sparks:
            pygame.draw.circle(surf, p[5], (int(p[0]), int(p[1])), max(2, p[4] // 4))
        if self.flash:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((255, 48, 168, 28))
            surf.blit(ov, (0, 0))
        if self.banner:
            lab = self.font_lg.render("BUMP", True, GOLD)
            surf.blit(lab, lab.get_rect(center=(W // 2, 300)))
        title = self.font_lg.render(TITLE, True, GOLD)
        surf.blit(title, title.get_rect(center=(W // 2, 78)))
        sub = self.font_sm.render(HANDLE, True, PINK)
        surf.blit(sub, sub.get_rect(center=(W // 2, 140)))
        sc = self.font.render(f"SCORE  {self.score}", True, WHITE)
        cb = self.font_sm.render(f"STREAK  x{self.combo}   BALLS  {self.balls}", True, CYAN)
        hint = self.font_sm.render("Z / LEFT   flip   X / RIGHT", True, AMBER)
        surf.blit(sc, sc.get_rect(center=(W // 2, H - 150)))
        surf.blit(cb, cb.get_rect(center=(W // 2, H - 96)))
        surf.blit(hint, hint.get_rect(center=(W // 2, H - 48)))

    def play_interactive(self):
        running = True
        while running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                    running = False
            keys = pygame.key.get_pressed()
            self.lf = keys[pygame.K_z] or keys[pygame.K_LEFT] or keys[pygame.K_a]
            self.rf = keys[pygame.K_x] or keys[pygame.K_RIGHT] or keys[pygame.K_d]
            self.tick()
            self.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()

    def record(self):
        frames = FPS * SECS
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart",
            OUT,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        canvas = pygame.Surface((W, H))
        try:
            for i in range(frames):
                self.autoplay()
                self.tick()
                self.draw(canvas)
                proc.stdin.write(pygame.image.tostring(canvas, "RGB"))
                if i % 30 == 0:
                    print(f"frame {i}/{frames}", flush=True)
        finally:
            proc.stdin.close()
            err = proc.stderr.read().decode("utf-8", "ignore")
            rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed ({rc}):\n{err[-1200:]}")
        print("wrote", OUT)
        pygame.quit()


def main():
    g = Game()
    if PLAY and not RECORD:
        g.play_interactive()
    else:
        g.record()


if __name__ == "__main__":
    main()
