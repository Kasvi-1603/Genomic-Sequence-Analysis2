(function bootDnaHelix() {
  const root = document.getElementById("dna-helix-root");
  if (!root || !window.IgdaDnaHelix || typeof window.IgdaDnaHelix.mount !== "function") {
    return;
  }
  window.IgdaDnaHelix.mount(root);
})();
