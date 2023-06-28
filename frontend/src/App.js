import './App.css';
import Waveform from './components/Waveform';
import { useState } from 'react';
import { PaperAirplaneIcon } from '@heroicons/react/24/solid';

const API_ENDPOINT='https://rachelspark--musicgen-web-dev.modal.run'

function App() {
  const [prompt, setPrompt] = useState("");
  const [audioUrl, setAudioUrl] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    try {
      const response = await fetch(API_ENDPOINT + '/generate', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({
          "prompt": prompt
        })
      });
      const arrayBuffer = await response.arrayBuffer();
      const blob = new Blob([arrayBuffer], {type: 'audio/wav'});
      const objectURL = URL.createObjectURL(blob);
      setAudioUrl(objectURL); // update audioUrl state
      console.log(audioUrl)
    } catch(error) {
      console.error('Error:', error);
    }
  }

  async function onMount() {

  }

  return (
    <div className="min-w-full min-h-screen screen flex">
      <main className="bg-zinc-800 w-full flex justify-center">
        <div className="m-8 w-3/4 h-1/2 bg-zinc-700 rounded-xl shadow-lg flex flex-col justify-between items-center">
          <div className="text-center text-3xl text-white font-bold m-8">Tune Generator</div>
            <form className="relative w-1/2 flex flex-row" onSubmit={handleSubmit}>
              <input
                className="resize-none static rounded-lg w-full p-3 bg-zinc-600/50 text-lg text-white placeholder-white/50 hover:bg-zinc-600/75 focus:bg-zinc-600/75 focus:outline-none"
                id="prompt"
                placeholder="Describe tune here"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
              />
              <button type="submit" className="h-6 w-6 absolute top-4 right-2" onClick={handleSubmit}>
                <PaperAirplaneIcon className="text-green-400 h-4 w-4"/>
              </button>
            </form>
            <div className="w-3/4">
              <Waveform path={'/bach.mp3'}/>
            </div>
        </div>
      </main>
    </div>
  );
}

export default App;
