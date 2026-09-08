import React, {useEffect, useState} from 'react';
import {AbsoluteFill, Audio, Composition, continueRender, delayRender,
  cancelRender, interpolate, registerRoot, staticFile, useCurrentFrame} from 'remotion';

type Props = {seconds: number; audio: string | null};
const Tracer: React.FC<Props> = ({seconds, audio}) => {
  const frame = useCurrentFrame();
  const [handle] = useState(() => delayRender('local font ready'));
  useEffect(() => {
    const font = new FontFace('Inter', `url(${staticFile('fonts/Inter.ttf')})`);
    font.load().then((loaded) => {
      document.fonts.add(loaded);
      continueRender(handle);
    }).catch(cancelRender);
  }, [handle]);
  const scale = interpolate(frame, [0, seconds * 30 - 1], [1.12, 0.9],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{background: '#101828', color: '#fff',
    fontFamily: 'Inter', alignItems: 'center', justifyContent: 'center'}}>
    <div style={{fontSize: 64, fontWeight: 700, marginBottom: 80}}>Render boundary</div>
    <svg width="1000" height="500" viewBox="0 0 1000 500">
      <g transform={`translate(500 250) scale(${scale}) translate(-500 -250)`}>
        <rect x="80" y="150" width="340" height="200" rx="40" fill="#7258ec"/>
        <path d="M430 250 H560 M530 220 L565 250 L530 280" stroke="#fff" strokeWidth="10" fill="none"/>
        <rect x="580" y="150" width="340" height="200" rx="40" fill="#087f6d"/>
        <text x="250" y="275" textAnchor="middle" fill="white" fontSize="58">Make</text>
        <text x="750" y="275" textAnchor="middle" fill="white" fontSize="58">Check</text>
      </g>
    </svg>
    <div style={{fontSize: 40, marginTop: 100}}>Technical tracer · {seconds}s</div>
    {audio ? <Audio src={staticFile(audio)}/> : null}
  </AbsoluteFill>;
};
const Root = () => <Composition id="Video" component={Tracer} width={1080} height={1920}
  fps={30} durationInFrames={30} defaultProps={{seconds: 1, audio: null}}
  calculateMetadata={({props}) => {
    if (!Number.isFinite(props.seconds) || props.seconds < 1 || props.seconds > 120)
      throw new Error('seconds must be 1..120');
    return {durationInFrames: Math.round(props.seconds * 30)};
  }}/>;
registerRoot(Root);
