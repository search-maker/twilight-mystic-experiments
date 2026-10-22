from __future__ import annotations

import base64
import copy
import hashlib
import io
import json
import subprocess
import zipfile
import zlib
from pathlib import Path

V5_HEAD = '0d7ad7030aacc1c34bca93fef6c02fd7dcf776c2'
V5_SCRIPT_BLOB = '6bf506cc0af62a313461db168c614b3494d6a95f'
V5_SCRIPT = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v5/review_authorization.py'
V6_BRANCH = 'review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v6-20260910'
V6_SCRIPT = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v6/review_authorization.py'

HERE = Path(__file__).resolve()
REVIEW_ROOT = HERE.parents[2]
V5_ROOT = REVIEW_ROOT.parent / 'v5-base'

head = subprocess.run(
    ['git', '-C', str(V5_ROOT), 'rev-parse', 'HEAD'],
    text=True,
    capture_output=True,
    check=False,
)
if head.returncode != 0 or head.stdout.strip() != V5_HEAD:
    raise RuntimeError(f'frozen V5 source checkout drift: {head.stdout!r} {head.stderr!r}')

v5_path = V5_ROOT / V5_SCRIPT
raw = v5_path.read_bytes()
git_blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
if git_blob != V5_SCRIPT_BLOB:
    raise RuntimeError(f'frozen V5 source blob drift: {git_blob}')

# Recover the exact effective V5 source without executing its reviewer entry point.  The frozen
# V5 wrapper is itself a deterministic transformation of exact V4 bytes; keeping that builder
# intact preserves every accepted V4/V5 repair while this successor adds only the authorized
# spent-NON_AUTH diagnostic artifact classification.
v5_wrapper = raw.decode('utf-8')
terminal_exec = "exec(compile(patched, str(HERE), 'exec'), globals(), globals())"
if v5_wrapper.count(terminal_exec) != 1:
    raise RuntimeError('V6 frozen V5 terminal exec anchor drift')
extractor = v5_wrapper.replace(terminal_exec, 'V5_EFFECTIVE_SOURCE = patched', 1)
scope = {'__file__': str(HERE), '__name__': '_avps_v5_exact_source_builder_'}
exec(compile(extractor, str(HERE), 'exec'), scope, scope)
source = scope.get('V5_EFFECTIVE_SOURCE')
if not isinstance(source, str) or not source:
    raise RuntimeError('V6 could not recover exact effective V5 source')

# Mechanical identity lift only; substantive V6 changes are injected below with exact-site counts.
patched = source.replace('replacement-v5', 'replacement-v6').replace('REPLACEMENT_V5', 'REPLACEMENT_V6')
patched = patched.replace('v5', 'v6').replace('V5', 'V6')

helper_anchor = '\ndef selfobs(row, payload, rpr, rh):\n'
if patched.count(helper_anchor) != 1:
    raise RuntimeError('V6 spent diagnostic helper injection anchor drift')

helper_code = zlib.decompress(base64.b85decode(
    'c-qZ7X>Z#|vfuM7dh<R=dMn8kMV&yf@FbZX&t&Z&PUZn?7($b5+8k4)hKC)mp#T1=`XIY`$Vz4wy9Q)QWOY?_b=^h1y8ih7^7H2M>hk={=btw3F3$gcd3F8y;_WqgL;9}>{O$RF{OdikGz*isw}y{SZ&=;frEqOxO>OPkJ)=HC(rMr=W;PAx&TO?}%%Aw)j7?`tYESLej5+qyoiKN)<8xCQd-u3HWsf0yI-`%fZ1iZ4c1f0dNt_kiT@IX#vcmINmL=&ZN&PUUkux9BBEL`4@L!Ze2n3_MC~;{t$~=mfb`ka1mc{w#(HYs6J-1d9OK0FINgskJc|sP(cVT{CxM%8G_V46o{Jf2HM$!VsJ$0Prd@`NRt)+I4dU-*kpA(l0-(FePVli`;ws9~?&b*xYCe*@mEFDprhXG*Y5R=(_VNE6ry9MBqZW%w*f8%k8U5&Cl1xzE@KoaNz@xwcoA*a3Up4zkddgcUEYqgwCS-|MZ^{24A>B3_cTh3j_ab3%rPv(nBu$<VoH=Ee7cbBa^HVIZMk1h;pGmnM4{F-A%8un^#FYTG-yR%8)Q_GopwjC^7XW_2ca<OtIY&Ek3&viU|=Gczs1xwFy*<!^e%yVfQ@|@;HhRA<Bzxc5E^#1zGhtHcIK3rVB+x+UZEcge=f!=Ys3t2OtY-#!c#z?~0OSZd+<&4}+ts$9C;5CJp1Fspp7VuiaYc(Wr<ivsdjtwt>ahzL8?JzuM>9aOVpSD=K<u9lY!nY{(yoon;T#v4%0So4yWe5Jk_kzV@?%Dq#OP~E$S^BKg(pOV!wgM|WV(GTyOqcW7<hZ2+lw&R7=sPWaH3h?2E&d~xKKo`%_d%bQ6KihI*le*19Ec@$5O|a=XUmy8rEEH#Fni)Ir_N%wTu{eZSc~OyGF>sB`qVpa>8`(A`u-xA!k=%?ms5N0&fJOTfa|aqOW$Mud^&ZP-qK|=-?C?c6U<l3*_1Br>D2pHOP?LL^cZE#qJRkb5h-Ob{IA4M!yvCrckt@fE1v~q;})?Wu}zRB+f5Wcvc5MYbV#xt^9E}Uy-Ojidt)z2**ImtZ+^>?xL<zXC7U9R`jmehlHm2Oh@$Llj|gti@^25X2Y_;%Cl3RT4|H~uCQsjl6iyw~BRhk&C2rLH2J+t$H~W(?pCPWl?O3|mfqdUgEUQLKsr{cuuta!_>Xzo-Jwuu|D8(R23BHGM#n1ST<^9qsv)+*0+zv<>08risU~xb6djn7rVhzZfH$*T}n)>anI4kyhKVorT66KH++=XOZx%}G$VP9b#qKR|jhx9H6;}5-(DY6Z-ER65Y{9+e{9?jWnQ;M)5N#(|p#Oc%KU*V2RH=_aD05=6#_r`tBS$2YmO9?1BSKB+B0p_}5!e*7*=#jsYdz#%xp*t3r`jVZ&_?~?gZl<qEPCB03cH#KRQyeAKhba8di;qMA3!9W;$kXR_Y1>Z_QV7rr!ibIk8SZ|B_kNg+f544jT$QX02+cr%-aQy@wHp6oaK)%2^5z)7M<KFofZ>)iPzDapce6L{b4LSS*bjX;F>o%-A4SZ+W9b;x95k!Pz_~wjw<GU>+lK>wE&&1>Mg<&{_})aHr__4@ytvtH92XHTQWrTzj00`U4;{j;v=4<H(dVR)!X|sZ)5B|143fnS$W@bB3Moq8WM3>}Up=<VNnf4N57d{3G$g;U=l5xvr2J?AusW8Mh8ZKDSWsj%>Yu=P5hDlGjo6y(^XDDw1HQp{v%x)VHn0hTZkt>tF>C6O<Qw*boR3lavc9%aV=M3Z8?f;mTq{B{9)T4{;FK`o{Q3Io@<i5CmKSNPXOlc>+@+0VM}`mWI{In2fp6_ui~6YDg`;~{PZdtIc@2x)I^d9>WPDY@^^r#0a5mg6%2?Y+2@Z+)qQ_WqML1{JJ$KIggSe0BGJxz-ahqq)27pU5rUBqr0{|@@-M<2ei>=GjW(2^9-ELMNKatRfZG`!=;kgjA!kR($f^-30FM&Px2>6bYDL<u<gFqz8$mg_R#=R{|@0h=#@;)j?CmWnflLr)vWaFOpv^{ZY-3oFQP|5-wNEQ{{o99Q+Ac}&n5&g&c#ibxt-7JaqwlqYy*g=FJqaspEmvsF=TWC983Edsxd8*M)9&UA?a05Ahp?Qw(U#BwZ#x0>6s13B4$bW^bRGsPzJu(2Hu<)XS;}^in7`qwBS-Ry3@lg)gBZxra#AH^b9W6YdN^H87tqCiY>}0h=u5sZRXX-fLJDMAq%Odp%ZUtki9C}hnKc6vX)bx(~T0`-m;sqF<Tj=ZR;E;hDy3~Ztlbl8yFDYU}p=>TnOhS>AxYWKOKnXE3#4DzE5H({<#>|;NDK9Q-X_*+8mGd9LYLwr#j9X9?CRIwHT<~%t&I_T=oLdP*d{7CuzNzwanT-Qu0$c_VEcS(!7&W;t6CLuHN$YUmXwm0yKYuy@z)!u+S?QR&d{u*mZi9Z22RDQ)IlgNNjZ%<Jv9+{5RKPUW91~y-v?0UnA>8c%xSjv%#BmExko?6-POg8s`1tYtyP802l#a@@2K%jIHQDNtEcZDLQL$a+agf^0Ni>R>eckb|(K9B2U`5O;@Gi%wJfl{u>Rz$THQPe6x_L^~-Og%BwKF=KG%6i4@$>%NOEhrt3;1QN+fw}sgED|Yu3^f2k=Ff4ql~@4fWURe*O@zgN_lmrV^;xe)0GfCr7z?{oaLwVq=0UKeQPW)H&_PUF2&YWt147ZZZ>EghB}2;W@V@oQqER0dWaq1dSZ{Mx^W12y?oG4wq6HPHv?@wE6YJ`gQ}*Msj=Qw)sM%xaeEro>z~dW@-)cl&eWtMZitgMmTYB<wYf$$UteI(izo!*07Ed=*hl#jae$>ii4w0(4N<SnHAQ@JRKFW5PS4!y0`Bxd27avhWdxGFgWhTAaiM`46RRMicbHlAwensMo<QPl%4p8x99T!T!%m`hsdV<ASXM-Nb_KPmxRZGy0}a23ACm{XQc>V{ay+#w(MLazqQp}eu`%^UCYx{NgpFTMBDnTmMh}T^p!HK~lESUM<QnTTDq?Jh3aRYz|KZKPf%7lvp*);=Z>5^l)o2Z6-$m~Qs8O96wq-X)FDlzdPmKh6*qA%DWy9^AoMybN51-m2UNsl0IneImPKOVw*t~?AEd4+WaQO`7gDs6#^+EN(5)#x5z{EM5eIk*27+s=`JW!)sG$avqStQlTX!o7cYtlP@(kgYu<XVEec-7MQ>oq$2F}nlfdjvfUzvif(Mh-<iB*XkQ*>j!`y>jFfgb`HY8(ybKZq<2hplV_1BRA@-uYVa5wLxEQpMp6)@mggMl?PT@x@HXYimY5JasystV%54=&TLIA4qrMq9H$8UV#x!_43o*yCrQ*gkCiaPOl_}7fge^r7*hi1wV|BT31>W-aJT8q4S00oa+flU3B+PePgN9Z`^VRUU*yefeW}{{2*Qt#syaFmnM$k>Q6;r<P1R_}int~gb7moq<)(psa7+FQ;i(1-+{RK>)d7tulsd7GtF_cMiuxS0s7~<c#8+TeP#lAL6fElxFtO=%Pq4J3mMG**L7+MG40nqRNsX_WW}L(ry*3q%QvWkKewB@pp`l(<?@MK_^ihIu+~-Zm4dPH&Q=`*Tn+#T`K>6yf<JC_RAlHpa5-!L3v7#q9La~-D2!d0(EX<SiS<d<O`iATQ$)RVCXAERF0B{Rj0*B=$(aRy#&Ii*fUWF@!^+zY)B{+Y;0HIHHud*kG9Tc5wE=&|`J%SAeMrxqt+&JVomT#9*6N$DMsFY9kG^HHI*h7R1uT7HWQ6DcGMMqP?zEA>I&D0aCzlJ6#W?PFS!wi(w^P`d_&i|0NX38Ck&IToSkocuQ2{${!ZaXB$V1<x5k*gTuR({V&{*;I=8t_^~aIvH%k+-=79K@p7x5*>$M9yQx6{h}~cTeLx2Jc0hVnKwuM#=|ZbQBUhILAkT$wcO!0nXn<qrw&JVaCBx^06{@-RM>daFlpnu><vaCJ>xiHWntr11@(Me?0g~ABSTMI2PDIvjJMtt2aU010CNdo(>L?fvnK{(go6Sx=Z=n{h(?^BD}^0x)_j)JamwDUCO0g#G;JswbeD(U2b+*Zbf?XP6sY?AP6GD)o_pWhMRA{(<|LfZdFbudP?>2=U$EJY8km0v#sTf4bxjbS(7;^(S~VjF-faW-BnJ%=Toa@ZqI`9qH1a!;5wfwR;zH(RYHrw*5S|?*zPfgn3V!Cx`%5lJyl)4);pX-qBk_xT1U9~7=akutZOqHS-xyqx2d;r){P#H7^tip)09JV^t?BQ7i%0)s9QG%r-m%dnkZHe&l%11Zx&3OXgefu7<ThkE5<bT+M3p<a#=N_Pv?^3#-=XFQfJvX2dzXjMXXnf@pn~-q>N!k?bi4+Tag`V|9!e>7?u9yLT52sJ(#dRxv(uyu(d13y^4C$u%idoDj2h&)z(J1Xv)dd4BkvyYn`NaLR~E(b#BehP<5xHL3H%U>%F52+mY6h2GrI;(r%lLBzfbYItMS-{5+<}bZA@TGDp$tP$&dsoR%6iB-$vWGKs;^ctoaW^~nE{xuZP@Q(@vZR>va}%VB$32?$3~l03jx9uTSp>BmnTB?Lc2CLdfGY9SGjOj=iRHLKRjui{aSq1=gMwJt?f#FgTm*Fi(0ui8bknhEmtJPxRMFeFwDmlgy%F&d+)Hl&jpQqy}k@K*Tv6T_ubZpEul6j5~I8E*5S049LyF2_7wdIgS7k4k2jf7q@@Er^KpOEr9|jX!LAQ2NW|FPB&Ucd3}H8p*sBg}G&Z&vV*>VZK_LM^z?z;&Cc3**%Ya#&-CjFHK6p<P@?jOxqB+dhQO$Jg{d`1n2iR>(S)aES1Z3;=>I<-`0@c@TIU4D_zcK)#!V<S&00oR-v$e@f^Uh4M~ujQpQNRd_3<2q7nf*Z&8mbMUXy7R2<^*>?$eRmyN77F?@yyo=`A%XV2EHQAoogRbQ+LRs^cgwLaS2(qii$VP^7YGIQH(^z8K<r`GE{=*3qji&gD(dJ$M2nqC2_sd`U;<hv}1RX5m|%^*RGxCuU;R5wKSHBYHI+37<a_Ygy2E6QiBhSN^u_(}Cv;?J@sz3)8;!!2Pksp@y4@|o}9$NqEpk<afK2@k<Ctj38<AWJ@s1!t6{31k@~NHd^>g_;B60zS_?0`twnJbXk}PWc(n$eEwEFJ!TGCn_;JWfKbazk`2~*rEK@q1E{ZzgV!jHG;Ybf5g<H71N{Cxs{D7LL>1zz8WLi2LAvj&Iz2T-xId;@q3Z*#Db=&m=0CB-EnU4^fK1M)9ffuyvqr6bOAx-tX$YgKX@;q;kM*g>wC-T&Ug4l$gOU;6T5Bn$dtD&eH>E3K9wAZ@yD(3x0v8oygYg?driHTUxa)oYrOwdUV(@?X!6-L5G*_P5a@IMv|u?KWKfB8{X{_P^w%PTK0i4+GgK)<b8yYK@~iXf?4vyP=G;{#&7wyB5jpRK!3yL!#K-jbeXMDZLwqXY;{cGNzr;h8%y&RmGwCG07U_H!PM({65~*1SjFyCdE1>8WbbyzNaV|CDLi$w&U(+~ksZ0qzV@7bL5(0(hGRZG^3%_LwkCFSW2;84!+&*QQ2utS>F5k&$b6&cax0OdZhC(>POXUYYC^vX)jrp9=MfU!yCM6tC7)uWS5B*8Y)&'
)).decode('utf-8')

patched = patched.replace(helper_anchor, helper_code + helper_anchor, 1)

scan_anchor = (
    "    observations = ordinal_module.authoritative_global_ordinal_observations(payload, current_run_id=a.run)\n"
    "    nonself = [row for row in observations if not selfobs(row, payload, a.rpr, a.rh)]\n"
)
scan_replacement = (
    "    observations = ordinal_module.authoritative_global_ordinal_observations(payload, current_run_id=a.run)\n"
    "    spent_diagnostic_proof, observations = validate_spent_nonauth_diagnostic_artifacts(c, a, payload, observations)\n"
    "    nonself = [row for row in observations if not selfobs(row, payload, a.rpr, a.rh)]\n"
)
scan_sites = patched.count(scan_anchor)
if scan_sites != 2:
    raise RuntimeError(f'V6 expected exactly two global ordinal scan sites, got {scan_sites}')
patched = patched.replace(scan_anchor, scan_replacement)

fixture_call = '    ordinal_fixtures = ordinal45_marker_fixtures()\n'
if patched.count(fixture_call) != 2:
    raise RuntimeError('V6 expected two ordinal fixture call sites')
patched = patched.replace(fixture_call, fixture_call + '    spent_diagnostic_fixtures = spent_nonauth_diagnostic_fixtures()\n')

fixture_write = "    write(a.ev / 'ordinal45-marker-fixtures.json', ordinal_fixtures)\n"
if patched.count(fixture_write) != 2:
    raise RuntimeError('V6 expected two ordinal fixture evidence writes')
patched = patched.replace(
    fixture_write,
    fixture_write
    + "    write(a.ev / 'v6-spent-nonauth-diagnostic-fixtures.json', spent_diagnostic_fixtures)\n"
    + "    write(a.ev / 'v6-spent-nonauth-diagnostic-classification.json', spent_diagnostic_proof)\n",
)

receipt_anchor = "        'ordinal45MarkerFixtureSuitePassed': True,\n"
if patched.count(receipt_anchor) != 2:
    raise RuntimeError('V6 expected two receipt fixture anchors')
patched = patched.replace(
    receipt_anchor,
    receipt_anchor
    + "        'spentNonAuthDiagnosticFixtureSuitePassed': True,\n"
    + "        'spentNonAuthDiagnosticArtifactIds': [10156701172, 10159398397],\n"
    + "        'spentNonAuthDiagnosticClassificationExactIdentityOnly': True,\n",
)

# Fail at build-time if a broad artifact-name ignore or a third allowlisted artifact sneaks in.
if patched.count('validate_spent_nonauth_diagnostic_artifacts(c, a, payload, observations)') != 2:
    raise RuntimeError('V6 spent diagnostic validator call count drift')
if patched.count("'artifact': 10156701172") != 1 or patched.count("'artifact': 10159398397") != 1:
    raise RuntimeError('V6 exact spent artifact identity cardinality drift')
if 'startswith(\'avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-\')' in patched:
    raise RuntimeError('V6 broad diagnostic artifact name ignore forbidden')

V6_TRANSFORM_AUDIT = {
    'frozenV5Head': V5_HEAD,
    'frozenV5ScriptGitBlobSha1': V5_SCRIPT_BLOB,
    'globalOrdinalScanSitesPatched': scan_sites,
    'exactSpentDiagnosticArtifactIds': [10156701172, 10159398397],
    'classificationMode': 'EXACT_IMMUTABLE_IDENTITY_ONLY',
    'unknownThirdArtifactRemainsFatal': True,
    'protectedJobMustBeSkipped': True,
    'allEarlierV4V5RepairsCarriedByExactEffectiveSource': True,
}

exec(compile(patched, str(HERE), 'exec'), globals(), globals())
