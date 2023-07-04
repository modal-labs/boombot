function App() {
  return (
    <div class="relative min-w-full min-h-screen absolute inset-0 bg-[#161618]">
        <main class="w-full flex flex-col items-center">
          <a className="w-1/4 flex justify-center" target="_blank" rel="noopener noreferref" href="https://modal.com/docs/guide/discord-musicgen">
              <img className="w-full mt-20" src="./boombot-logo.svg"/>
          </a>
          <div className="text-5xl md:text-7xl font-bold text-white m-[-10px]">boombot</div>
          <div className="w-2/3 text-2xl font-medium text-white p-8 mx-10 text-center whitespace-pre-wrap">
            Generate any music sample in seconds
          </div>
          <div className="w-1/2 text-md font-light text-white pb-12 mx-10 text-center whitespace-pre-wrap">
            Join the Discord community and interact with boombot to discover the power of <a className="text-white hover:underline" target="_blank" rel="noopener noreferref" href="https://github.com/facebookresearch/audiocraft">
            MusicGen</a>
          </div>
          <a target="_blank" rel="noopener noreferref" href="https://discord.gg/CBekEF42">
              <button className="bg-[#9AEE86] py-4 px-6 font-bold text-zinc-900 text-xl rounded hover:bg-[#b8fca7]">Get Started</button>
          </a>
          <div className="w-2/3 pt-16 pb-20">
            <video controls >
            <source src="./fast-demo-web.mp4" type="video/mp4"/>
            </video>
          </div>
          <div className="absolute bottom-4 text-zinc-400">Built with <a className="hover:text-gray-300 hover:underline" target="_blank" rel="noopener noreferref" href="https://modal.com">Modal</a>  |  <a className="hover:text-gray-300 hover:underline" target="_blank" rel="noopener noreferref" href="https://github.com/modal-labs/boombot">Github repo</a></div>
        </main>
    </div>
  );
}
  
  const container = document.getElementById("react");
  ReactDOM.createRoot(container).render(<App />);