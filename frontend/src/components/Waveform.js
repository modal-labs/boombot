import React, { useRef, useEffect, useState } from "react";
import WaveSurfer from "wavesurfer.js";
import { PlayCircleIcon } from '@heroicons/react/24/solid';
import { PauseCircleIcon } from '@heroicons/react/24/solid';


export default function Waveform({ path }) {
    const wavesurferRef = useRef(null);
    const [wavesurferObj, setWavesurferObj] = useState();

    const [playing, setPlaying] = useState(false);
  
    useEffect(() => {
      if (wavesurferRef.current && !wavesurferObj) {
        setWavesurferObj(
            WaveSurfer.create({
                container: wavesurferRef.current,
                scrollParent: true,
                autoCenter: true,
                waveColor: 'rgb(133, 147, 132)',
                progressColor: 'rgb(101, 230, 90)',
                minPxPerSec: 80,
                barWidth: 2,
                barGap: 1,
                barRadius: 2,
            })
        )

      }

      return () => {
        if (wavesurferObj) {
          wavesurferObj.destroy();
          console.log('WaveSurfer instance destroyed', wavesurferObj);
        }
      };
    }, [wavesurferRef, wavesurferObj]);

	useEffect(() => {
		if (path && wavesurferObj) {
			wavesurferObj.load(path);
		}
	}, [path, wavesurferObj]);


	useEffect(() => {
		if (wavesurferObj) {
			// once the waveform is ready, play the audio
			// wavesurferObj.on('ready', () => {
			// 	wavesurferObj.play();
			// 	// wavesurferObj.enableDragSelection({}); // to select the region to be trimmed
			// 	// setDuration(Math.floor(wavesurferObj.getDuration())); // set the duration in local state
			// });

			// once audio starts playing, set the state variable to true
			wavesurferObj.on('play', () => {
				setPlaying(true);
			});

			// once audio starts playing, set the state variable to false
			wavesurferObj.on('finish', () => {
				setPlaying(false);
			});

			// if multiple regions are created, then remove all the previous regions so that only 1 is present at any given time
			// wavesurferObj.on('region-updated', (region) => {
			// 	const regions = region.wavesurfer.regions.list;
			// 	const keys = Object.keys(regions);
			// 	if (keys.length > 1) {
			// 		regions[keys[0]].remove();
			// 	}
			// });
		}
	}, [wavesurferObj]);

    const handlePlayPause = (e) => {
		wavesurferObj.playPause();
		setPlaying(!playing);
	};

	const handleReload = (e) => {
		// stop will return the audio to 0s, then play it again
		wavesurferObj.stop();
		wavesurferObj.play();
		setPlaying(true); // to toggle the play/pause button icon
	};
      
    return(
        <div className="grid grid-cols-12 items-center bg-zinc-200 rounded-lg">
            <button
                title='play/pause'
                className='col-start-1 col-span-2 controls'
                onClick={handlePlayPause}>
                {playing ? (
                    <PauseCircleIcon className="h-16 w-16 text-green-400"/>
                ) : (
                    <PlayCircleIcon className="h-16 w-16 text-green-400"/>
                )}
            </button>
            <div id="waveform" className="col-start-3 col-span-9" ref={wavesurferRef}/>
        </div>
    )
}