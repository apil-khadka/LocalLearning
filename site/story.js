const storySteps = [...document.querySelectorAll('[data-story-step]')]
const storyFrames = [...document.querySelectorAll('[data-story-frame]')]
const storyCaption = document.querySelector('#story-image-caption strong')

function showStoryFrame(index) {
  const selectedFrame = storyFrames.find((frame) => frame.dataset.storyFrame === String(index))
  if (!selectedFrame) return

  storyFrames.forEach((frame) => {
    const isActive = frame === selectedFrame
    frame.classList.toggle('is-active', isActive)
    frame.setAttribute('aria-hidden', String(!isActive))
  })

  storySteps.forEach((step) => {
    if (step.dataset.storyStep === String(index)) {
      step.setAttribute('aria-current', 'step')
    } else {
      step.removeAttribute('aria-current')
    }
  })

  if (storyCaption) storyCaption.textContent = selectedFrame.dataset.caption ?? ''
}

function updateStoryFromScroll() {
  const centerLine = window.innerHeight * 0.58
  const activeStep = storySteps.find((step) => {
    const bounds = step.getBoundingClientRect()
    return bounds.top <= centerLine && bounds.bottom >= centerLine
  })

  if (activeStep) showStoryFrame(Number(activeStep.dataset.storyStep))
}

if (storySteps.length && storyFrames.length) {
  let scrollFramePending = false
  showStoryFrame(0)

  window.addEventListener(
    'scroll',
    () => {
      if (scrollFramePending) return
      scrollFramePending = true
      window.requestAnimationFrame(() => {
        updateStoryFromScroll()
        scrollFramePending = false
      })
    },
    { passive: true },
  )

  window.addEventListener('resize', updateStoryFromScroll, { passive: true })
}
