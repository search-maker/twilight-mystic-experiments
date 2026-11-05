import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const d=JSON.parse(readFileSync(new URL('./paranal-ubvri-empirical.json',import.meta.url),'utf8'));
const expected={U:[11.78,1.376,-0.039,.24],B:[11.84,1.411,-0.041,.12],V:[11.84,1.518,-0.057,.18],R:[11.40,1.567,-0.064,.29],I:[10.93,1.470,-0.062,.40]};
const nearly=(x,y,tol=1e-9)=>assert.ok(Math.abs(x-y)<=tol,`mismatch ${x} vs ${y}`);
const model=(band,dep)=>{
 const c=d.publishedFit.coefficients[band];
 if(!c||typeof dep!=='number'||!Number.isFinite(dep)||dep<5||dep>15)return null;
 const x=dep-5;
 return c.a0+c.a1*x+c.a2*x*x;
};
assert.equal(d.source.doi,'10.1051/0004-6361:20064992');
assert.deepEqual(d.publishedFit.domainSunDepressionDeg,[5,15]);
assert.equal(d.publishedFit.noExtrapolation,true);
for (const [band,arr] of Object.entries(expected)) {
 const c=d.publishedFit.coefficients[band];
 for(let i=0;i<4;i++)nearly([c.a0,c.a1,c.a2,c.rms][i],arr[i]);
}
assert.equal(model('V',15.000001),null);
assert.equal(model('V',16),null);
assert.equal(model('V','11'),null);
assert.equal(model('V',null),null);
assert.equal(model('Q',11),null);
nearly(model('V',11),18.896);
nearly(model('V',15),21.32);
assert.equal(d.derivedFitReference.length,6);
for(const row of d.derivedFitReference){
 for(const band of Object.keys(expected))nearly(model(band,row.sunDepressionDeg),row.magPerSquareArcsecond[band],1.1e-6);
}
const change=model('V',15)-model('V',11);
nearly(d.computedWithinBandV.deltaMag11to15,change);
nearly(d.computedWithinBandV.totalSkyVFluxRatio11to15,10**(.4*change),1e-8);
assert.deepEqual(d.publishedDirectionalSpectra.map(s=>s.sunDepressionDeg),[11.9,14.8]);
for(const s of d.publishedDirectionalSpectra)assert.ok(s.skyAltitudeDeg>=5&&s.skyAltitudeDeg<=80);
assert.equal(d.projectState.protectedOpened,false);
assert.equal(d.projectState.newScientificRun,false);
assert.equal(d.projectState.modelCoefficientsModified,false);
assert.equal(d.projectState.liveReleaseModified,false);
console.log('PASS_PARANAL_ORIGINAL_TABLE1_TABLE2_FIT_TRANSCRIPTION_DOMAIN_AND_ZERO_RELEASE_CLAIM');
