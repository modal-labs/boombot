function App() {
    return (
      <div class="relative min-w-full min-h-screen absolute inset-0 bg-zinc-900">
          <main class="w-full flex flex-col items-center overflow-auto">
            <a className="w-1/4 flex justify-center" target="_blank" rel="noopener noreferref" href="https://modal.com">
                <img className="w-full pt-20" src="./boombot-logo.svg"/>
            </a>
            <div className="text-5xl md:text-7xl font-bold text-white p-2">boombot</div>
            <div className="w-1/2 text-lg text-white p-8 pb-12 mx-10 text-center whitespace-pre-wrap">Create any music you want, with a simple text prompt.

            Join the Discord community and explore the power of <a className="text-white hover:underline" target="_blank" rel="noopener noreferref" href="https://github.com/facebookresearch/audiocraft">
            MusicGen.</a></div>
            <a target="_blank" rel="noopener noreferref" href="https://discord.gg/CBekEF42">
                <button className="bg-[#9AEE86] py-4 px-6 font-bold text-zinc-900 text-xl rounded hover:bg-[#b8fca7]">Try it out</button>
            </a>
            <div className="absolute bottom-2 text-zinc-400">Built with <a className="hover:text-gray-300 hover:underline" target="_blank" rel="noopener noreferref" href="https://modal.com">Modal</a></div>
          </main>
      </div>
    );
  }
  
  const container = document.getElementById("react");
  ReactDOM.createRoot(container).render(<App />);