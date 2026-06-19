export type ToastType = 'success' | 'error' | 'info' | 'warning';

export function showToast(message: string, type: ToastType = 'info', duration: number = 4000) {
  if (typeof window === 'undefined') return;

  // Create or get container
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none';
    document.body.appendChild(container);
  }

  // Create toast element
  const toast = document.createElement('div');
  
  // Style and colors based on type
  let bgClass = 'bg-slate-800 border-slate-700 text-slate-100 border';
  let svgIcon = `
    <svg class="w-5 h-5 text-blue-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
    </svg>
  `;

  if (type === 'success') {
    bgClass = 'bg-emerald-950/90 border-emerald-500/50 text-emerald-100 border';
    svgIcon = `
      <svg class="w-5 h-5 text-emerald-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
      </svg>
    `;
  } else if (type === 'error') {
    bgClass = 'bg-rose-950/90 border-rose-500/50 text-rose-100 border';
    svgIcon = `
      <svg class="w-5 h-5 text-rose-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
      </svg>
    `;
  } else if (type === 'warning') {
    bgClass = 'bg-amber-950/90 border-amber-500/50 text-amber-100 border';
    svgIcon = `
      <svg class="w-5 h-5 text-amber-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
      </svg>
    `;
  }

  toast.className = `flex items-start gap-3 p-4 rounded-xl shadow-2xl backdrop-blur-md transition-all duration-300 transform translate-x-full opacity-0 pointer-events-auto ${bgClass}`;
  toast.innerHTML = `
    ${svgIcon}
    <div class="flex-grow text-sm font-medium leading-relaxed">${message}</div>
    <button class="text-xs opacity-50 hover:opacity-100 flex-shrink-0 ml-1 select-none focus:outline-none">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
      </svg>
    </button>
  `;

  // Auto remove
  const timeoutId = setTimeout(() => {
    closeToast();
  }, duration);

  // Close button functionality
  toast.querySelector('button')?.addEventListener('click', () => {
    clearTimeout(timeoutId);
    closeToast();
  });

  function closeToast() {
    toast.classList.add('translate-x-full', 'opacity-0');
    setTimeout(() => {
      toast.remove();
      if (container && container.childElementCount === 0) {
        container.remove();
      }
    }, 300);
  }

  container.appendChild(toast);

  // Animate in
  requestAnimationFrame(() => {
    toast.classList.remove('translate-x-full', 'opacity-0');
  });
}
