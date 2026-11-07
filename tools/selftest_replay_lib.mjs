// selftest_replay_lib.mjs - replays a version 3 black-box export through the dashboard's REAL
// sensor pipeline (parseFrame, Madgwick, calibration, self-healing, mount, touchDirs), pulled
// out of handrig_dashboard.html by name. Used by verify_selftest_replay.mjs.
//
// What can't be replayed: frames the black box did not record (the gap between the end of the
// guided run and the self-test). The filters just continue across it, so heading drift that
// happened in the gap is lost. Tilt recovers from gravity within a second.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const NL = String.fromCharCode(10);

// Just enough of three.js r128 for the code paths used here (x,y,z,w storage order).
const THREE_SRC = `
class Quaternion{constructor(x=0,y=0,z=0,w=1){this.x=x;this.y=y;this.z=z;this.w=w;}
 set(x,y,z,w){this.x=x;this.y=y;this.z=z;this.w=w;return this;}
 copy(q){return this.set(q.x,q.y,q.z,q.w);}
 clone(){return new Quaternion(this.x,this.y,this.z,this.w);}
 invert(){this.x=-this.x;this.y=-this.y;this.z=-this.z;return this;}
 length(){return Math.hypot(this.x,this.y,this.z,this.w);}
 normalize(){const l=this.length()||1;return this.set(this.x/l,this.y/l,this.z/l,this.w/l);}
 multiply(q){return this.multiplyQuaternions(this,q);}
 premultiply(q){return this.multiplyQuaternions(q,this);}
 multiplyQuaternions(a,b){const ax=a.x,ay=a.y,az=a.z,aw=a.w,bx=b.x,by=b.y,bz=b.z,bw=b.w;
  return this.set(ax*bw+aw*bx+ay*bz-az*by, ay*bw+aw*by+az*bx-ax*bz, az*bw+aw*bz+ax*by-ay*bx, aw*bw-ax*bx-ay*by-az*bz);}
 setFromAxisAngle(a,t){const s=Math.sin(t/2);return this.set(a.x*s,a.y*s,a.z*s,Math.cos(t/2));}
 dot(q){return this.x*q.x+this.y*q.y+this.z*q.z+this.w*q.w;}
 slerp(qb,t){if(t===0)return this;if(t===1)return this.copy(qb);
  const x=this.x,y=this.y,z=this.z,w=this.w;let c=w*qb.w+x*qb.x+y*qb.y+z*qb.z;
  if(c<0){this.set(-qb.x,-qb.y,-qb.z,-qb.w);c=-c;}else this.copy(qb);
  if(c>=1){return this.set(x,y,z,w);}
  const s2=1-c*c;if(s2<=Number.EPSILON){const s=1-t;this.set(s*x+t*this.x,s*y+t*this.y,s*z+t*this.z,s*w+t*this.w);return this.normalize();}
  const s=Math.sqrt(s2),h=Math.atan2(s,c),ra=Math.sin((1-t)*h)/s,rb=Math.sin(t*h)/s;
  return this.set(x*ra+this.x*rb,y*ra+this.y*rb,z*ra+this.z*rb,w*ra+this.w*rb);}
}
class Vector3{constructor(x=0,y=0,z=0){this.x=x;this.y=y;this.z=z;}
 set(x,y,z){this.x=x;this.y=y;this.z=z;return this;} copy(v){return this.set(v.x,v.y,v.z);}
 applyQuaternion(q){const x=this.x,y=this.y,z=this.z,qx=q.x,qy=q.y,qz=q.z,qw=q.w;
  const ix=qw*x+qy*z-qz*y,iy=qw*y+qz*x-qx*z,iz=qw*z+qx*y-qy*x,iw=-qx*x-qy*y-qz*z;
  return this.set(ix*qw+iw*-qx+iy*-qz-iz*-qy, iy*qw+iw*-qy+iz*-qx-ix*-qz, iz*qw+iw*-qz+ix*-qy-iy*-qx);}
}
const THREE={Quaternion,Vector3};`;

export function loadPage(file = join(here, "handrig_dashboard.html")) {
  const html = readFileSync(file, "utf8");
  const script = html.match(/<script>([\s\S]*)<\/script>/)[1];
  const grab = re => { const m = script.match(re); if (!m) throw new Error("not found in page: " + re); return m[0]; };
  const fn = name => {
    const i = script.indexOf("function " + name + "(");
    if (i < 0) throw new Error("function not found: " + name);
    const eol = script.indexOf(NL, i);
    if (script.slice(i, eol).trimEnd().endsWith("}")) return script.slice(i, eol);
    return script.slice(i, script.indexOf(NL + "}", i) + 2);
  };
  const line = re => grab(new RegExp("^" + re + ".*$", "m"));
  const src = [
    THREE_SRC,
    grab(/const META=\[[\s\S]*?\];/), line("const SYNC=0xAB"), grab(/const ACC_OFFSET=\[[^\n]*/),
    grab(/const REMAPS=\{[\s\S]*?\n\};/), line("let REMAP_OF="),
    grab(/class Madgwick\{[\s\S]*?\n\}/), grab(/const S=META\.map[\s\S]*?\}\)\);/),
    grab(/const GYR_CLIP_DPS=[\s\S]*?let betaUser=[^\n]*/), line("const _rz="),
    grab(/const MOUNT_TAU_S=[\s\S]*?let handMount=[^\n]*/), grab(/const _hv=[^\n]*/), line("const _mv="),
    line("const mountFit="), line("const ACCFIT_EVERY_S="), line("const ACCFIT_R_TOL="), line("const accFit="),
    line("const STILL_DEV_DPS="), line("const _hq="), line("const r3="),
    grab(/const FINGER_ANCHORS=\{[\s\S]*?\n\};/), line("const THUMB_BASE_FRAC="),
    grab(/\/\/ ===== hand kinematics =====[\s\S]*?\/\/ ===== end hand kinematics =====/),
    grab(/\/\/ ===== touch detection =====[\s\S]*?\/\/ ===== end touch detection =====/),
    ...["applyRemap", "parseFrame", "healStillness", "healBeta", "healRezero", "learnAccOffset", "solve4",
      "learnMount", "setHandMount", "setMountTilt", "finishCalibration", "refHeading", "alignHeadings",
      "handRelQuat", "touchDirs", "touchMeter", "activeTouches"].map(fn),
    script.includes("function nearPair(") ? "" : "const nearPair=null;",
  ].join(NL);
  const stubs = `
const T={now:0}; const performance={now:()=>T.now};
const localStorage={getItem:()=>null,setItem(){}};
const document={getElementById:()=>({classList:{remove(){},add(){}},style:{},textContent:""})};
let runRec=null,lastSeq=-1,lostWin=0,totWin=0,framesWin=0,lastT=0,recording=false,recFrames=[];
let calState="idle",calAcc=null,calTimer=null,calOnDone=null,guided=null,selfT=null,batchActive=false;
let touchTemplates=[],tplOn={},TOUCH_MODEL=null,touchOn=[],zeroEpoch=0;

function pushHist(){} function pushBatchRaw(){} function bbFrame(){} function setStatus(){} function updateButtons(){} function clearInterval(){}
function bbLog(){}`;
  return new Function(stubs + NL + src + `
return {T,S,ACC_OFFSET,parseFrame,nearPair,handDefault,digitTip,digitBase,contactFix,unrollQs,buildWarp,thumbWarp,warpHand,PAIR_FINGER,finishCalibration,touchDirs,handRelQuat,touchMeter,templateTouch,digitDist,
  makeTemplate,finishTemplates,setHandMount,DEG,
  startCal(){calAcc=META.map(()=>({n:0,gs:[0,0,0],gq:[0,0,0],as:[0,0,0]}));S.forEach(st=>st.calGyroEMA=null);calState="run";},
  setMode(g,s){guided=g;selfT=s;},
  setTemplates(t){touchTemplates=t;},
  zeroNow(){S.forEach(st=>st.qRef.copy(st.fil.three()));alignHeadings();},
  state(){return {calState,guided,selfT};}};`)();
}

// One raw black-box row -> the 80-byte BLE frame parseFrame expects.
export function frameOf(row, seq) {
  const b = new Uint8Array(80), dv = new DataView(b.buffer);
  dv.setUint8(0, 0xAB); dv.setUint8(1, seq & 0xff); dv.setUint32(2, row[0] >>> 0, true); dv.setUint8(6, row[1]);
  let off = 7;
  for (let s = 0; s < 6; s++) for (let a = 0; a < 6; a++) {
    const v = row[2 + 6 * s + a] * (a < 3 ? 8192 : 16.384);
    dv.setInt16(off, Math.max(-32768, Math.min(32767, Math.round(v))), true); off += 2;
  }
  return b;
}

// Replays the run. Calls onFrame(i, msRel) after each frame, where i is the raw row index.
// Mode follows the marks: calibration during STILL, guided until the run ends, self-test after.
export function replay(cal, L, onFrame) {
  const rows = cal.raw.rows, t0 = rows[0][0];
  const accOff = cal.session.sensors.map(s => s.accOffset);
  accOff.forEach((o, i) => { L.ACC_OFFSET[i] = o.slice(); });   // the offsets in use at export (unknown at start)
  L.setHandMount(cal.session.mount.psiDeg * Math.PI / 180);
  const still = cal.marks.find(m => m.name === "STILL");
  const selfStart = cal.marks.find(m => m.name.startsWith("SELF")).f0;
  L.startCal();
  L.setMode({ phase: "still" }, null);
  for (let i = 0; i < rows.length; i++) {
    L.T.now = rows[i][0] - t0;
    if (i === still.f1) { L.finishCalibration(); L.setMode({ phase: "run" }, null); }
    if (i === selfStart) L.setMode(null, { i: 0 });
    L.parseFrame(frameOf(rows[i], i));
    onFrame && onFrame(i, L.T.now);
  }
}
