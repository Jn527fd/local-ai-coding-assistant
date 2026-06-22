const output = document.querySelector("#output");

export function formatGreeting(name) {
  return `Hello, ${name}!`;
}

if (output) {
  output.textContent = formatGreeting("developer");
}
