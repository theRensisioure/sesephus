"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const htmlPath = path.join(__dirname, "index.html");
const html = fs.readFileSync(htmlPath, "utf8");
const found = html.match(/<script>([\s\S]*?)<\/script>/);
if (!found) throw new Error("index.html has no inline script");
const script = found[1];
if (/\brequire\s*\(/.test(script) || /\bimport\s/.test(script)) {
  throw new Error("page script must run without Node module or require");
}

const sandbox = {
  window: {},
  document: {
    getElementById: function () { return null; },
    readyState: "complete",
    addEventListener: function () {},
  },
  performance: globalThis.performance,
  console: console,
  requestAnimationFrame: function () { return 0; },
  Float32Array: Float32Array,
  Uint8Array: Uint8Array,
  Uint8ClampedArray: Uint8ClampedArray,
  Uint32Array: Uint32Array,
  Math: Math,
  Date: Date,
  Object: Object,
  Array: Array,
  Number: Number,
  isFinite: isFinite,
  isNaN: isNaN,
};
vm.createContext(sandbox);
vm.runInContext(script, sandbox, { filename: "index.html" });
const MUUD = sandbox.window.MUUD;
if (!MUUD || typeof MUUD.stepCar !== "function" || typeof MUUD.advance !== "function") {
  throw new Error("shipped script did not publish MUUD on window");
}

const failures = [];
function check(name, cond, extra) {
  if (cond) {
    console.log("PASS " + name);
    return;
  }
  const line = "FAIL " + name + (extra ? " " + extra : "");
  console.error(line);
  failures.push(line);
}

function run(car, input, seconds) {
  const want = Math.round(seconds / MUUD.FIXED_DT);
  let steps = 0;
  const chunk = MUUD.FIXED_DT * 4;
  while (steps < want) steps += MUUD.advance(car, input, chunk);
  return car;
}

function rear(car) {
  const tires = car.tiresLast.filter(function (t) { return t.name.charAt(0) === "R"; });
  return {
    alpha: tires.reduce(function (s, t) { return s + Math.abs(t.alpha); }, 0) / tires.length,
    mu: tires.reduce(function (s, t) { return s + t.muA; }, 0) / tires.length,
    kappa: tires.reduce(function (s, t) { return s + t.kappa; }, 0) / tires.length,
  };
}

const gravel = MUUD.surfaces.gravel;
const mud = MUUD.surfaces.mud;

if (!/<canvas[^>]*width="960"[^>]*height="600"/.test(html)) {
  failures.push("FAIL canvas is not the 960 by 600 drawing buffer");
}
check("view size", MUUD.VIEW.w === 960 && MUUD.VIEW.h === 600);

{
  function go(chunk, times) {
    const car = MUUD.createCar({ u: 10 });
    const input = { throttle: 0.4, brake: 0, steer: 0.12, handbrake: false, drive: "rwd" };
    let steps = 0;
    for (let i = 0; i < times; i++) steps += MUUD.advance(car, input, chunk);
    return { steps: steps, u: car.u, v: car.v, r: car.r, x: car.x, y: car.y, yaw: car.yaw };
  }
  const fine = go(MUUD.FIXED_DT, 200);
  const mid = go(MUUD.FIXED_DT * 2, 100);
  const coarse = go(MUUD.FIXED_DT * 4, 50);
  check("same step count", fine.steps === 200 && mid.steps === 200 && coarse.steps === 200, [fine.steps, mid.steps, coarse.steps].join(","));
  check("same car state", fine.x === mid.x && fine.x === coarse.x && fine.yaw === mid.yaw && fine.yaw === coarse.yaw && fine.u === mid.u && fine.r === coarse.r);
}

{
  const powered = MUUD.weightTransfer(5, 0);
  const braked = MUUD.weightTransfer(-5, 0);
  const corner = MUUD.weightTransfer(0, 4);
  check("throttle loads rear", powered.RL + powered.RR > powered.FL + powered.FR);
  check("brake loads front", braked.FL + braked.FR > braked.RL + braked.RR);
  check("corner loads outside", corner.FL + corner.RL > corner.FR + corner.RR);
  const heavy = MUUD.tireForce(0, gravel.latPeakAt, powered.RL, gravel, 1);
  const light = MUUD.tireForce(0, gravel.latPeakAt, powered.FL, gravel, 1);
  check("load changes grip", Math.abs(heavy.fy) > Math.abs(light.fy));
  const latOnly = MUUD.tireForce(0, gravel.latPeakAt, 3000, gravel, 1);
  const combined = MUUD.tireForce(gravel.longPeakAt, gravel.latPeakAt, 3000, gravel, 1);
  const longOnly = MUUD.tireForce(gravel.longPeakAt, 0, 3000, gravel, 1);
  check("circle cuts cornering", Math.abs(combined.fy) < Math.abs(latOnly.fy) * 0.97);
  check("circle cuts drive", Math.abs(combined.fx) < Math.abs(longOnly.fx) * 0.97);
}

{
  const pushed = run(MUUD.createCar({ u: 8 }), { throttle: 1, brake: 0, steer: 0, handbrake: false, drive: "rwd" }, 0.5);
  check("throttle accel", pushed.ax > 0.4, "ax " + pushed.ax.toFixed(2));
  const pushedLoads = MUUD.weightTransfer(pushed.ax, pushed.ay);
  check("live throttle load", pushedLoads.RL + pushedLoads.RR > pushedLoads.FL + pushedLoads.FR);
  const slowed = run(MUUD.createCar({ u: 16 }), { throttle: 0, brake: 1, steer: 0, handbrake: false, drive: "rwd" }, 0.45);
  check("brake accel", slowed.ax < -0.4, "ax " + slowed.ax.toFixed(2));
  const brakedLoads = MUUD.weightTransfer(slowed.ax, slowed.ay);
  check("live brake load", brakedLoads.FL + brakedLoads.FR > brakedLoads.RL + brakedLoads.RR);
}

{
  const car = MUUD.createCar({ u: 15 });
  const input = { throttle: 1, brake: 0, steer: 0.3, handbrake: false, drive: "rwd" };
  let yawPos = 0;
  let samples = 0;
  let crossed = null;
  const limit = Math.round(2.5 / MUUD.FIXED_DT);
  let steps = 0;
  while (steps < limit && !crossed) {
    steps += MUUD.advance(car, input, MUUD.FIXED_DT * 2);
    const slip = rear(car);
    samples++;
    if (car.r > 0.25) yawPos++;
    if (slip.alpha > gravel.latPeakAt && slip.mu < gravel.peakGrip) {
      crossed = { alpha: slip.alpha, mu: slip.mu, r: car.r };
    }
  }
  check("slip past the peak", !!crossed, crossed ? JSON.stringify(crossed) : "never");
  check("sustained yaw", yawPos > samples * 0.6, yawPos + "/" + samples);
  const yawAtFlip = car.yaw;
  const rateAtFlip = car.r;
  input.steer = -input.steer;
  run(car, input, 0.9);
  check(
    "reverse steer reverses yaw",
    rateAtFlip > 0 && car.r < 0 && car.yaw < yawAtFlip - 0.15,
    "dy " + (car.yaw - yawAtFlip).toFixed(2) + " r " + car.r.toFixed(2)
  );
}

{
  function yawOf(drive) {
    return run(MUUD.createCar({ u: 14 }), { throttle: 0.9, brake: 0, steer: 0.3, handbrake: false, drive: drive }, 1.3).yaw;
  }
  const fwd = Math.abs(yawOf("fwd"));
  const rwd = Math.abs(yawOf("rwd"));
  check("fwd understeers rwd", fwd < rwd * 0.8, fwd.toFixed(2) + " vs " + rwd.toFixed(2));
  const shares = { fwd: MUUD.driveShares("fwd"), rwd: MUUD.driveShares("rwd"), awd: MUUD.driveShares("awd") };
  check("fwd torque on the front", shares.fwd[0] > 0 && shares.fwd[2] === 0 && shares.rwd[2] > 0 && shares.rwd[0] === 0);
  check("awd splits torque", shares.awd[0] > 0 && shares.awd[2] > 0 && shares.awd[0] < shares.rwd[2]);
}

{
  function betas(drive) {
    const car = MUUD.createCar({ u: 7, v: 8, r: 1.2 });
    const series = [];
    for (let i = 0; i < 6; i++) {
      run(car, { throttle: 1, brake: 0, steer: 0, handbrake: false, drive: drive }, 0.2);
      series.push(Math.abs(Math.atan2(car.v, car.u)));
    }
    return series;
  }
  function firstUnder(series, limitBeta) {
    for (let i = 0; i < series.length; i++) if (series[i] < limitBeta) return i;
    return series.length;
  }
  const rwd = betas("rwd");
  const awd = betas("awd");
  check(
    "awd pulls out faster",
    firstUnder(awd, 0.12) < firstUnder(rwd, 0.12) && awd[1] < rwd[1] * 0.6,
    "awd " + awd.map(function (n) { return n.toFixed(3); }).join(" ") + " rwd " + rwd.map(function (n) { return n.toFixed(3); }).join(" ")
  );
}

{
  function meanRate(handbrake) {
    const car = MUUD.createCar({ u: 16 });
    const input = { throttle: 0, brake: 0, steer: 0.34, handbrake: handbrake, drive: "rwd" };
    let acc = 0;
    let n = 0;
    const want = Math.round(1 / MUUD.FIXED_DT);
    let steps = 0;
    while (steps < want) {
      steps += MUUD.advance(car, input, MUUD.FIXED_DT * 2);
      acc += Math.abs(car.r);
      n++;
    }
    return acc / n;
  }
  const open = meanRate(false);
  const locked = meanRate(true);
  check("handbrake adds yaw", locked > open * 1.15, open.toFixed(3) + " -> " + locked.toFixed(3));
}

{
  const one = MUUD.createGrid(MUUD.PATCH, MUUD.PATCH, 8);
  const ten = MUUD.createGrid(MUUD.PATCH, MUUD.PATCH, 8);
  MUUD.carveLoop(one, { laps: 1, load: 2800, slipRatio: 0.05 });
  MUUD.carveLoop(ten, { laps: 10, load: 2800, slipRatio: 0.05 });
  check("ten laps deeper", MUUD.gridMax(ten) > MUUD.gridMax(one) * 4, MUUD.gridMax(one).toFixed(4) + " vs " + MUUD.gridMax(ten).toFixed(4));
  const light = MUUD.createGrid(MUUD.PATCH, MUUD.PATCH, 8);
  const heavy = MUUD.createGrid(MUUD.PATCH, MUUD.PATCH, 8);
  const spun = MUUD.createGrid(MUUD.PATCH, MUUD.PATCH, 8);
  MUUD.carveLoop(light, { laps: 2, load: 900, slipRatio: 0 });
  MUUD.carveLoop(heavy, { laps: 2, load: 4500, slipRatio: 0 });
  MUUD.carveLoop(spun, { laps: 2, load: 900, slipRatio: 1.1 });
  check("load digs more", MUUD.gridMax(heavy) > MUUD.gridMax(light));
  check("wheelspin digs more", MUUD.gridMax(spun) > MUUD.gridMax(light));
  const picture = MUUD.rasterCells(ten, 160, 100, { x: 0, y: 0, viewW: 30 });
  const blank = MUUD.rasterCells(MUUD.createGrid(MUUD.PATCH, MUUD.PATCH, 8), 160, 100, { x: 0, y: 0, viewW: 30 });
  function darkFraction(buf) {
    let dark = 0;
    let seen = 0;
    for (let i = 0; i < buf.length; i += 16) {
      seen++;
      if (buf[i + 3] > 0 && buf[i] < 100) dark++;
    }
    return dark / seen;
  }
  check("groove is drawn", darkFraction(picture) > darkFraction(blank) + 0.02, darkFraction(picture).toFixed(3));
}

{
  const grid = MUUD.createGrid(MUUD.PATCH, MUUD.PATCH, 8);
  for (let i = 0; i < grid.depth.length; i++) {
    const row = (i / grid.cols) | 0;
    const cy = grid.originY + (row + 0.5) * grid.cell;
    if (cy > 0) grid.depth[i] = 0.7;
  }
  check("slope pulls toward the rut", MUUD.slopePull(grid, 0, 0, 0, mud) > 0);
  check("depth lowers grip", MUUD.mudGripScale(0, mud) > MUUD.mudGripScale(0.8, mud));
  check("depth adds drag", MUUD.mudDrag(0.8, 6, 3000, mud) > MUUD.mudDrag(0, 6, 3000, mud));
  const low = MUUD.tireForce(0, mud.latPeakAt, 3000, mud, MUUD.mudGripScale(0.8, mud));
  const high = MUUD.tireForce(0, mud.latPeakAt, 3000, mud, MUUD.mudGripScale(0, mud));
  check("grip scale feeds the same tire", Math.abs(low.fy) < Math.abs(high.fy));
  const tugged = run(
    MUUD.createCar({ u: 9, mud: true, grid: grid, surface: mud }),
    { throttle: 0, brake: 0, steer: 0, handbrake: false, drive: "rwd" },
    0.8
  );
  const flat = run(
    MUUD.createCar({ u: 9 }),
    { throttle: 0, brake: 0, steer: 0, handbrake: false, drive: "rwd" },
    0.8
  );
  check("car tugs into the rut", tugged.y > flat.y + 0.15, tugged.y.toFixed(3) + " vs " + flat.y.toFixed(3));
}

{
  const grid = MUUD.createGrid(MUUD.PATCH, MUUD.PATCH, 8);
  const car = MUUD.createCar({ u: 0.15, mud: true, grid: grid, surface: mud });
  car.tires.forEach(function (tire) {
    if (!tire.rear) return;
    const at = MUUD.bodyPointWorld(car, tire.x, tire.y);
    MUUD.setDisc(grid, at[0], at[1], 3.2, 0.55);
  });
  function depthUnderRear() {
    let sum = 0;
    let n = 0;
    car.tires.forEach(function (tire) {
      if (!tire.rear) return;
      const at = MUUD.bodyPointWorld(car, tire.x, tire.y);
      sum += MUUD.sampleDepth(grid, at[0], at[1]);
      n++;
    });
    return sum / n;
  }
  const before = depthUnderRear();
  const uBefore = car.u;
  run(car, { throttle: 1, brake: 0, steer: 0, handbrake: false, drive: "rwd" }, 0.45);
  const spun = rear(car);
  const dug = depthUnderRear();
  check("floor spins the tire", spun.kappa > mud.longPeakAt * 2, "k " + spun.kappa.toFixed(2));
  check("floor digs", dug > before + 0.01, before.toFixed(3) + " -> " + dug.toFixed(3));
  check("floor adds no speed", car.u < uBefore + 0.2, "u " + car.u.toFixed(3));
  const uMid = car.u;
  run(car, { throttle: 0.22, brake: 0, steer: 0, handbrake: false, drive: "rwd" }, 1.4);
  const hooked = rear(car);
  const after = depthUnderRear();
  check("ease drives", car.u > uMid + 0.25, uMid.toFixed(3) + " -> " + car.u.toFixed(3));
  check("ease stops the spin dig", hooked.kappa < spun.kappa * 0.5 && (after - dug) < (dug - before));
}

{
  const low = MUUD.measureRutFrame(4);
  const high = MUUD.measureRutFrame(16);
  check("higher resolution touches more cells", high.cellsTouched > low.cellsTouched * 2, low.cellsTouched + " -> " + high.cellsTouched);
  check(
    "rut cost is timed work",
    Number.isFinite(low.ms) && Number.isFinite(high.ms) && low.maxDepth > 0 && high.paint > 0 && high.ms > low.ms,
    low.ms.toFixed(2) + " ms / " + high.ms.toFixed(2) + " ms"
  );
  const wallStart = globalThis.performance.now();
  const mid = MUUD.measureRutFrame(8);
  const wall = globalThis.performance.now() - wallStart;
  check(
    "reported ms comes from that call",
    Number.isFinite(mid.ms) && mid.ms >= 0 && mid.ms <= wall + 20 && mid.paint > 0,
    "inner " + mid.ms.toFixed(2) + " wall " + wall.toFixed(2)
  );
  const sweep = MUUD.sweepRutCost([4, 8, 16, 32]);
  let rising = true;
  for (let i = 1; i < sweep.length; i++) if (sweep[i].cellsTouched <= sweep[i - 1].cellsTouched) rising = false;
  check("sweep touches more as cells per car rise", rising, sweep.map(function (row) { return row.cellsPerCarLength + ":" + row.cellsTouched; }).join(" "));
  console.log(MUUD.formatSweep(sweep));
  MUUD._sweep = sweep;
}

if (failures.length) {
  console.error(failures.length + " failed");
  process.exit(1);
}
console.log("ALL PASS");
