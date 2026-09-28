document.addEventListener("DOMContentLoaded", () => {
  const sos = document.getElementById("sosBtn");
  if (sos) {
    sos.addEventListener("click", () => {
      if (!confirm("Send your current location to DAOYOU Admin?")) return;
      const send = (lat=null, lon=null) => {
        fetch("/sos", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            latitude: lat,
            longitude: lon,
            message: "Tourist activated SOS 24/7"
          })
        }).then(r => r.json()).then(() => alert("SOS recorded. DAOYOU support has been notified in this demo."));
      };
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          p => send(p.coords.latitude, p.coords.longitude),
          () => send()
        );
      } else send();
    });
  }

  const timer = document.querySelector(".timer[data-expiry]");
  if (timer) {
    const expiry = new Date(timer.dataset.expiry).getTime();
    const tick = () => {
      const diff = Math.max(0, expiry - Date.now());
      const m = String(Math.floor(diff / 60000)).padStart(2, "0");
      const s = String(Math.floor((diff % 60000) / 1000)).padStart(2, "0");
      timer.textContent = `${m}:${s}`;
      if (diff <= 0) timer.classList.add("expired");
    };
    tick();
    setInterval(tick, 1000);
  }
});
