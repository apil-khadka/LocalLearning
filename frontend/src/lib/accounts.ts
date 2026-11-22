export function generateTemporaryPassword() {
  const bytes = window.crypto.getRandomValues(new Uint8Array(18))
  return `Temp-${Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')}`
}
