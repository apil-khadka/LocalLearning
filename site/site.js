const routes = {
  student: {
    nodes: [
      ['Student device', 'Phone, laptop or classroom display'],
      ['School Wi-Fi', 'Local router and isolated student network'],
      ['Student portal', 'Locally bundled web app and public API'],
      ['Approved content', 'Books, Kiwix articles and Kolibri lessons'],
    ],
    caption:
      'Core learning travels over the LAN. Articles and videos must be downloaded and verified before the WAN is disconnected.',
  },
  tutor: {
    nodes: [
      ['A learner’s question', 'Grade, subject, chapter and chosen language'],
      ['Private application API', 'Validate input and retrieve relevant passages'],
      ['Local AI services', 'Ollama inference and a dedicated Qdrant index'],
      ['Answer and source chips', 'Retrieved pages to check with a teacher'],
    ],
    caption:
      'The browser never talks directly to the model or vector database. If a dependency fails, the portal reports it. If no passage matches, there are no textbook source chips.',
  },
  staff: {
    nodes: [
      ['Staff laptop', 'On a separate management network'],
      ['SSH tunnel', 'Encrypted connection to server loopback'],
      ['Staff listener', 'Separate entry point and Bearer authentication'],
      ['Approved import', 'Bounded PDF/text ingestion and diagnostics'],
    ],
    caption:
      'The student reverse proxy blocks staff endpoints. Staff credentials stay in page memory. NOMAD and router management need their own protected network paths.',
  },
}
const flow = document.getElementById('network-flow')
const caption = document.getElementById('network-caption')
function selectRoute(name) {
  const route = routes[name]
  flow.replaceChildren(
    ...route.nodes.map(([title, description]) => {
      const node = document.createElement('div')
      node.className = 'flow-node'
      const heading = document.createElement('strong')
      const paragraph = document.createElement('p')
      heading.textContent = title
      paragraph.textContent = description
      node.append(heading, paragraph)
      return node
    }),
  )
  caption.textContent = route.caption
  document
    .querySelectorAll('[data-route]')
    .forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.route === name)))
}
document
  .querySelectorAll('[data-route]')
  .forEach((button) => button.addEventListener('click', () => selectRoute(button.dataset.route)))
selectRoute('student')
