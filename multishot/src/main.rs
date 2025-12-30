
use macroquad::prelude::*;

// -------- Performance-first window config --------
// - sample_count = 1 disables MSAA (lower GPU cost). :contentReference[oaicite:5]{index=5}
fn window_conf() -> Conf {
    Conf {
        window_title: "Multishot (Rust, low requirements)".to_string(),
        window_width: 1280,
        window_height: 720,
        high_dpi: false,      // keep render resolution low for older hardware
        sample_count: 1,      // MSAA off
        window_resizable: false,
        ..Default::default()
    }
}

#[derive(Clone, Copy)]
struct Target {
    x: f32,
    y: f32,
    spawn_t: f64, // seconds (macroquad time)
    life_s: f32,  // seconds
}

#[derive(Default)]
struct Stats {
    score: i32,
    shots: u32,
    kills: u32,
    expired: u32,
    rt_sum_s: f32,
    rt_n: u32,
}

struct Config {
    duration_s: f32,      // timed mode length
    target_count: usize,
    target_life_s: f32,   // base lifetime (randomized slightly per target)
    margin_px: f32,       // keep spawns away from edges
    min_r: f32,
    max_r: f32,

    base_points: i32,
    speed_bonus: i32,
    miss_penalty: i32,
    expire_penalty: i32,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            duration_s: 60.0,
            target_count: 3,
            target_life_s: 0.90,
            margin_px: 80.0,
            min_r: 10.0,
            max_r: 28.0,

            base_points: 100,
            speed_bonus: 100,
            miss_penalty: 50,
            expire_penalty: 75,
        }
    }
}

struct Game {
    cfg: Config,
    targets: Vec<Target>,
    stats: Stats,

    practice: bool,
    finished: bool,
    start_t: f64,

    // tiny optimization: update HUD string at ~20Hz, not every frame
    hud_cache: String,
    hud_next_update: f64,

    cursor_grabbed: bool,
}

impl Game {
    fn new(cfg: Config) -> Self {
        // Seed macroquad RNG (avoids repeatable spawn patterns).
        // macroquad provides srand/rand/gen_range. :contentReference[oaicite:6]{index=6}
        let seed = (std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos() as u64)
            ^ 0x9E37_79B9_7F4A_7C15;
        rand::srand(seed);

        let mut g = Self {
            cfg,
            targets: Vec::new(),
            stats: Stats::default(),
            practice: false,
            finished: false,
            start_t: get_time(),
            hud_cache: String::new(),
            hud_next_update: 0.0,
            cursor_grabbed: false,
        };

        g.reset(get_time());
        g
    }

    fn reset(&mut self, now: f64) {
        self.stats = Stats::default();
        self.finished = false;
        self.start_t = now;

        self.targets.clear();
        self.targets.reserve(self.cfg.target_count);

        for _ in 0..self.cfg.target_count {
            let t = self.spawn_target(now);
            self.targets.push(t);
        }

        self.hud_cache.clear();
        self.hud_next_update = 0.0;
    }

    fn spawn_target(&self, now: f64) -> Target {
        let w = screen_width();
        let h = screen_height();

        // Clamp margin so we never produce invalid ranges on small windows.
        let mut m = self.cfg.margin_px;
        m = m.min(w * 0.45).min(h * 0.45);

        let life = self.cfg.target_life_s * rand::gen_range(0.85, 1.15);

        // Try a few times to avoid heavy overlap (cheap & good enough).
        for _ in 0..24 {
            let x = if w > 2.0 * m { rand::gen_range(m, w - m) } else { w * 0.5 };
            let y = if h > 2.0 * m { rand::gen_range(m, h - m) } else { h * 0.5 };

            let mut ok = true;
            let min_sep = (self.cfg.max_r * 2.2).powi(2);

            for t in &self.targets {
                let dx = x - t.x;
                let dy = y - t.y;
                if dx * dx + dy * dy < min_sep {
                    ok = false;
                    break;
                }
            }

            if ok {
                return Target { x, y, spawn_t: now, life_s: life };
            }
        }

        // fallback: just place it somewhere valid
        let x = if w > 2.0 * m { rand::gen_range(m, w - m) } else { w * 0.5 };
        let y = if h > 2.0 * m { rand::gen_range(m, h - m) } else { h * 0.5 };
        Target { x, y, spawn_t: now, life_s: life }
    }

    fn radius_at(&self, age_s: f32, life_s: f32) -> f32 {
        // Triangle wave grow->shrink, with a cheap ease-out.
        let p = (age_s / life_s).clamp(0.0, 1.0);
        let tri = if p < 0.5 { p * 2.0 } else { (1.0 - p) * 2.0 };
        let eased = 1.0 - (1.0 - tri) * (1.0 - tri); // easeOutQuad

        self.cfg.min_r + (self.cfg.max_r - self.cfg.min_r) * eased
    }

    fn alpha_at(&self, age_s: f32, life_s: f32) -> f32 {
        let p = (age_s / life_s).clamp(0.0, 1.0);
        if p < 0.85 {
            1.0
        } else {
            ((1.0 - p) / 0.15).clamp(0.15, 1.0)
        }
    }

    fn shoot(&mut self, now: f64, mx: f32, my: f32) {
        self.stats.shots += 1;

        let mut hit_i: Option<usize> = None;

        // With tiny N (3 targets), linear scan is fastest/simplest.
        for (i, t) in self.targets.iter().enumerate() {
            let age_s = (now - t.spawn_t) as f32;
            let r = self.radius_at(age_s, t.life_s);
            let dx = mx - t.x;
            let dy = my - t.y;

            if dx * dx + dy * dy <= r * r {
                hit_i = Some(i);
                // break: first hit is fine for small N
                break;
            }
        }

        if let Some(i) = hit_i {
            let t = self.targets[i];
            let age_s = (now - t.spawn_t) as f32;
            let p = (age_s / t.life_s).clamp(0.0, 1.0);

            self.stats.kills += 1;
            self.stats.rt_sum_s += age_s;
            self.stats.rt_n += 1;

            let pts = self.cfg.base_points + ((self.cfg.speed_bonus as f32) * (1.0 - p)).round() as i32;
            self.stats.score += pts;

            self.targets[i] = self.spawn_target(now);
        } else {
            self.stats.score -= self.cfg.miss_penalty;
        }

        if self.stats.score < 0 {
            self.stats.score = 0;
        }
    }

    fn update(&mut self) {
        let now = get_time();

        // Exit
        if is_key_pressed(KeyCode::Escape) {
            std::process::exit(0);
        }

        // Toggles / restart
        if is_key_pressed(KeyCode::R) {
            self.reset(now);
        }
        if is_key_pressed(KeyCode::P) {
            self.practice = !self.practice;
            self.reset(now);
        }
        if is_key_pressed(KeyCode::G) {
            self.cursor_grabbed = !self.cursor_grabbed;
            // macroquad exposes cursor grab + cursor visibility. :contentReference[oaicite:7]{index=7}
            set_cursor_grab(self.cursor_grabbed);
            show_mouse(!self.cursor_grabbed);
        }

        if self.finished {
            return;
        }

        // Timed end
        if !self.practice {
            let elapsed_s = (now - self.start_t) as f32;
            if elapsed_s >= self.cfg.duration_s {
                self.finished = true;
                // restore cursor when run ends
                set_cursor_grab(false);
                show_mouse(true);
                self.cursor_grabbed = false;
                return;
            }
        }

        // Expire targets
        for i in 0..self.targets.len() {
            let t = self.targets[i];
            let age_s = (now - t.spawn_t) as f32;
            if age_s >= t.life_s {
                self.stats.expired += 1;
                self.stats.score = (self.stats.score - self.cfg.expire_penalty).max(0);
                self.targets[i] = self.spawn_target(now);
            }
        }

        // Shoot input
        if is_mouse_button_pressed(MouseButton::Left) {
            let (mx, my) = mouse_position();
            self.shoot(now, mx, my);
        }

        // Update HUD text ~20Hz to reduce allocations
        if now >= self.hud_next_update {
            let elapsed_s = (now - self.start_t) as f32;
            let time_left = if self.practice {
                f32::INFINITY
            } else {
                (self.cfg.duration_s - elapsed_s).max(0.0)
            };

            let shot_acc = if self.stats.shots > 0 {
                (self.stats.kills as f32) / (self.stats.shots as f32)
            } else {
                0.0
            };

            let target_acc = {
                let denom = self.stats.kills + self.stats.expired;
                if denom > 0 {
                    (self.stats.kills as f32) / (denom as f32)
                } else {
                    0.0
                }
            };

            let avg_rt_ms = if self.stats.rt_n > 0 {
                (self.stats.rt_sum_s / self.stats.rt_n as f32) * 1000.0
            } else {
                0.0
            };

            // macroquad exposes FPS counters. :contentReference[oaicite:8]{index=8}
            let fps = get_fps();

            self.hud_cache = if self.practice {
                format!(
                    "PRACTICE (∞)\nScore: {}\nKills: {}  Expired: {}\nShots: {}  ShotAcc: {:>3}%\nTargetAcc: {:>3}%\nAvg RT: {:>4.0} ms\nFPS: {}",
                    self.stats.score,
                    self.stats.kills,
                    self.stats.expired,
                    self.stats.shots,
                    (shot_acc * 100.0).round() as i32,
                    (target_acc * 100.0).round() as i32,
                    avg_rt_ms,
                    fps
                )
            } else {
                format!(
                    "TIME: {:>4.1}s\nScore: {}\nKills: {}  Expired: {}\nShots: {}  ShotAcc: {:>3}%\nTargetAcc: {:>3}%\nAvg RT: {:>4.0} ms\nFPS: {}",
                    time_left,
                    self.stats.score,
                    self.stats.kills,
                    self.stats.expired,
                    self.stats.shots,
                    (shot_acc * 100.0).round() as i32,
                    (target_acc * 100.0).round() as i32,
                    avg_rt_ms,
                    fps
                )
            };

            self.hud_next_update = now + 0.05;
        }
    }

    fn draw(&self) {
        // Simple flat background
        clear_background(Color::new(0.04, 0.06, 0.08, 1.0)); // Color::new() exists in macroquad. :contentReference[oaicite:9]{index=9}

        let now = get_time();

        // Targets
        for t in &self.targets {
            let age_s = (now - t.spawn_t) as f32;
            let r = self.radius_at(age_s, t.life_s);
            let a = self.alpha_at(age_s, t.life_s);

            let fill = Color::new(0.28, 0.85, 0.85, 0.18 * a + 0.08);
            let rim  = Color::new(0.28, 0.85, 0.85, 0.95 * a);
            let dot  = Color::new(0.92, 0.95, 0.98, 0.95 * a);

            // draw_circle / draw_circle_lines are provided by macroquad shapes. :contentReference[oaicite:10]{index=10}
            draw_circle(t.x, t.y, r, fill);
            draw_circle_lines(t.x, t.y, r, 2.0, rim);
            draw_circle(t.x, t.y, (r * 0.18).max(2.0), dot);
        }

        // Crosshair at cursor
        let (mx, my) = mouse_position();
        draw_line(mx - 10.0, my, mx - 4.0, my, 2.0, Color::new(0.92, 0.95, 0.98, 0.85)); // draw_line signature. :contentReference[oaicite:11]{index=11}
        draw_line(mx + 4.0, my, mx + 10.0, my, 2.0, Color::new(0.92, 0.95, 0.98, 0.85));
        draw_line(mx, my - 10.0, mx, my - 4.0, 2.0, Color::new(0.92, 0.95, 0.98, 0.85));
        draw_line(mx, my + 4.0, mx, my + 10.0, 2.0, Color::new(0.92, 0.95, 0.98, 0.85));
        draw_circle(mx, my, 1.5, Color::new(0.92, 0.95, 0.98, 0.9));

        // HUD
        draw_text(&self.hud_cache, 16.0, 24.0, 22.0, Color::new(0.90, 0.93, 0.97, 0.90));

        if self.finished {
            let msg = "RUN COMPLETE\nR = Restart   P = Practice";
            let w = measure_text(msg, None, 38, 1.0).width;
            draw_text(
                msg,
                screen_width() * 0.5 - w * 0.5,
                screen_height() * 0.5,
                38.0,
                Color::new(0.95, 0.97, 1.0, 0.95),
            );
        }
    }
}

#[macroquad::main(window_conf)]
async fn main() {
    let cfg = Config::default();
    let mut game = Game::new(cfg);

    loop {
        // IMPORTANT: macroquad runs frames as fast as possible,
        // so all time-based logic should use elapsed time / timers, not “frame counts”. :contentReference[oaicite:12]{index=12}
        game.update();
        game.draw();
        next_frame().await;
    }
}

