const menuBtn = document.getElementById("menuBtn");
const mobileMenu = document.getElementById("mobileMenu");
const menuIcon = document.getElementById("menuIcon");

function openMenu() {
  mobileMenu.classList.remove("opacity-0", "pointer-events-none", "scale-95", "translate-y-2");
  menuIcon.className = "fa-solid fa-xmark text-xl";
}

function closeMenu() {
  mobileMenu.classList.add("opacity-0", "pointer-events-none", "scale-95", "translate-y-2");
  menuIcon.className = "fa-solid fa-bars text-xl";
}

menuBtn.addEventListener("click", () => {
  if (mobileMenu.classList.contains("opacity-0")) {
    openMenu();
  } else {
    closeMenu();
  }
});

document.addEventListener("click", (e) => {
  if (!mobileMenu.classList.contains("opacity-0") &&
      !mobileMenu.contains(e.target) &&
      !menuBtn.contains(e.target)) {
    closeMenu();
  }
});

document.querySelectorAll("#mobileMenu a").forEach((link) => {
  link.addEventListener("click", closeMenu);
});



const navLinks = document.querySelectorAll(".nav-link");
const indicator = document.getElementById("nav-indicator");

function updateIndicator(link) {
  if (!indicator || !link) return;
  navLinks.forEach((l) => {
    l.classList.remove("active");
    l.classList.add("text-on-surface-variant");
  });
  link.classList.add("active");
  link.classList.remove("text-on-surface-variant");
  link.classList.add("text-primary");
  indicator.style.width = link.offsetWidth + "px";
  indicator.style.left = link.offsetLeft + "px";
}

const sections = {};
navLinks.forEach((link) => {
  const section = document.getElementById(link.dataset.section);
  if (section) sections[link.dataset.section] = section;
});

const sectionObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const link = document.querySelector(
          ".nav-link[data-section=\"" + entry.target.id + "\"]"
        );
        if (link) updateIndicator(link);
      }
    });
  },
  { threshold: 0.3, rootMargin: "-80px 0px 0px 0px" }
);

Object.values(sections).forEach((s) => sectionObserver.observe(s));

if (navLinks.length > 0) {
  updateIndicator(navLinks[0]);
}

document.querySelectorAll("a[href^=\"#\"]").forEach((anchor) => {
  anchor.addEventListener("click", (e) => {
    e.preventDefault();
    const target = document.querySelector(anchor.getAttribute("href"));
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });
});

const GOOGLE_FORM_URL = "https://docs.google.com/forms/u/0/d/e/1FAIpQLScpc958TX2-5Re1W6cwiLF9eIpBs4jPLUwdNN67buoQYSsKBw/formResponse";

const FIELD_MAP = {
  nombre: "entry.1096373761",
  telefono: "entry.734686186",
  tipo_entidad: "entry.727672707",
  institucion: "entry.590929523",
  zona: "entry.1109345739",
  tema: "entry.921465563",
  fecha: "entry.1298642196",
  asistentes: "entry.748141868",
  publico: "entry.593455377",
};

let isSubmitting = false;
let cooldownActive = false;

const form = document.getElementById("charlaForm");
const successMsg = document.getElementById("formSuccess");

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const submitBtn = form.querySelector("button[type=\"submit\"]");
  const originalText = submitBtn.innerHTML;

  if (cooldownActive) {
    successMsg.innerHTML = '<i class="fa-solid fa-hourglass mr-2"></i>Por favor espera 60 segundos antes de enviar otra solicitud.';
    successMsg.className = "p-4 rounded-lg border text-sm text-center";
    successMsg.classList.remove("hidden");
    setTimeout(() => successMsg.classList.add("hidden"), 4000);
    return;
  }

  if (isSubmitting) return;

  isSubmitting = true;
  submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i>Enviando...';

  const checkTimer = setTimeout(() => {
    submitBtn.innerHTML = '<i class="fa-solid fa-circle-check mr-2"></i>Enviado';
  }, 3000);

  try {
    const fd = new FormData(form);
    const body = new FormData();
    for (const [field, entryId] of Object.entries(FIELD_MAP)) {
      const value = fd.get(field);
      if (value) body.append(entryId, value);
    }
    await fetch(GOOGLE_FORM_URL, { method: "POST", mode: "no-cors", body });
    form.reset();
    cooldownActive = true;
    successMsg.innerHTML = '<i class="fa-solid fa-circle-check mr-2"></i>¡Solicitud recibida! Nuestro equipo se comunicará con usted en breve.';
    successMsg.className = "p-4 rounded-lg bg-primary/5 border border-primary/20 text-primary text-sm text-center";
    successMsg.classList.remove("hidden");
    setTimeout(() => successMsg.classList.add("hidden"), 8000);
    setTimeout(() => {
      cooldownActive = false;
      isSubmitting = false;
      submitBtn.innerHTML = originalText;
    }, 60000);
  } catch {
    clearTimeout(checkTimer);
    isSubmitting = false;
    submitBtn.innerHTML = originalText;
    successMsg.innerHTML = '<i class="fa-solid fa-circle-exclamation mr-2"></i>Error de conexión. Intente nuevamente.';
    successMsg.className = "p-4 rounded-lg bg-error/5 border border-error/20 text-error text-sm text-center";
    successMsg.classList.remove("hidden");
    setTimeout(() => successMsg.classList.add("hidden"), 6000);
  }
});

const revealElements = document.querySelectorAll(".reveal");
const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("reveal-visible");
      }
    });
  },
  { threshold: 0.1 }
);
revealElements.forEach((el) => observer.observe(el));

// Modal
const MODAL_CONTENT = {
  privacidad: {
    titulo: "Aviso de Privacidad",
    html: `<p>En cumplimiento con la normativa vigente en materia de protección de datos personales, la <strong>Sede de Prevención del Delito Barinas</strong> pone a disposición de los usuarios el siguiente aviso de privacidad.</p>
<p><strong>Responsable del tratamiento:</strong> Sede de Prevención del Delito Barinas, institución gubernamental adscrita al ejecutivo nacional.</p>
<p><strong>Datos recolectados:</strong> Los datos personales solicitados a través del formulario de solicitud de charla preventiva incluyen: nombre del solicitante, teléfono de contacto, tipo de entidad, nombre de la institución, parroquia o zona, fecha sugerida, cantidad estimada de asistentes y público objetivo. Estos datos son proporcionados voluntariamente por el usuario.</p>
<p><strong>Finalidad:</strong> Los datos serán utilizados exclusivamente para coordinar, programar y dar seguimiento a las actividades formativas solicitadas, así como para generar estadísticas anónimas sobre el alcance e impacto de los programas preventivos.</p>
<p><strong>Almacenamiento:</strong> La información se almacena en Google Sheets institucional bajo la administración del equipo designado. Se mantendrá durante el tiempo necesario para cumplir con las finalidades descritas y conforme a los plazos de conservación establecidos por la normativa aplicable.</p>
<p><strong>No cesión a terceros:</strong> Los datos personales no serán compartidos, transferidos ni cedidos a terceros ajenos a esta institución, salvo obligación legal o requerimiento de autoridad competente.</p>
<p><strong>Derechos ARCO:</strong> Los titulares de los datos tienen derecho a acceder, rectificar, cancelar u oponerse al tratamiento de sus datos personales. Para ejercer estos derechos, puede contactarnos a través de los canales oficiales de la institución.</p>
<p><strong>Consentimiento:</strong> Al enviar el formulario de solicitud, el usuario otorga su consentimiento expreso para el tratamiento de sus datos personales conforme a lo descrito en este aviso.</p>`
  },
  terminos: {
    titulo: "Términos y Condiciones",
    html: `<p>Los siguientes términos y condiciones regulan el acceso y uso del sitio web de la <strong>Sede de Prevención del Delito Barinas</strong>.</p>
<p><strong>Naturaleza del sitio:</strong> Este es un sitio web institucional de carácter público e informativo, cuyo propósito es difundir los programas preventivos ofrecidos por la institución y facilitar la solicitud de charlas formativas.</p>
<p><strong>Uso del sitio:</strong> El usuario se compromete a utilizar el sitio web y sus servicios de conformidad con la ley, la moral, el orden público y las presentes condiciones. Queda prohibido el uso del sitio con fines ilícitos o que puedan causar daño a terceros.</p>
<p><strong>Contenido informativo:</strong> La información proporcionada en este sitio tiene carácter meramente informativo y no constituye asesoría legal. La institución se reserva el derecho de modificar, actualizar o eliminar contenidos sin previo aviso.</p>
<p><strong>Disponibilidad:</strong> La institución no garantiza la disponibilidad continua e ininterrumpida del sitio, pudiendo ocurrir interrupciones por mantenimiento, causas técnicas o fuerza mayor.</p>
<p><strong>Propiedad intelectual:</strong> Los contenidos, diseño gráfico, logotipos y material audiovisual presentes en este sitio son propiedad de la institución o se utilizan con la debida autorización. Queda prohibida su reproducción total o parcial sin autorización expresa.</p>
<p><strong>Legislación aplicable:</strong> El uso de este sitio web se rige por las leyes de la República Bolivariana de Venezuela. Cualquier controversia derivada del uso del sitio será sometida a la jurisdicción de los tribunales competentes.</p>`
  },
  transparencia: {
    titulo: "Transparencia",
    html: `<p>La <strong>Sede de Prevención del Delito Barinas</strong> reafirma su compromiso con la transparencia, la rendición de cuentas y el derecho de acceso a la información pública.</p>
<p><strong>Datos públicos:</strong> En la sección "Impacto en Cifras" de este sitio web se publican dashboards interactivos con datos agregados y anónimos sobre las solicitudes de charlas preventivas recibidas, incluyendo: total de solicitudes, beneficiarios estimados, entidades alcanzadas, parroquias participantes, distribución por tema y tipo de entidad, y evolución temporal de las solicitudes.</p>
<p><strong>Confidencialidad:</strong> Los datos personales de los solicitantes (nombre, teléfono) no son publicados en los dashboards públicos. Se protege estrictamente la identidad de los ciudadanos que solicitan los servicios institucionales.</p>
<p><strong>Actualización:</strong> Los datos presentados en los dashboards se actualizan periódicamente conforme se reciben nuevas solicitudes, reflejando en tiempo real el alcance de los programas preventivos.</p>
<p><strong>Solicitudes de información:</strong> Los ciudadanos pueden ejercer su derecho de acceso a la información pública dirigiendo su solicitud a través de los canales oficiales de la institución. Se dará respuesta dentro de los plazos establecidos por la ley.</p>
<p><strong>Compromiso:</strong> Esta institución se compromete a mantener informada a la comunidad sobre sus actividades, resultados y el uso de los recursos públicos destinados a la prevención del delito y la promoción de una cultura de paz.</p>`
  }
};

const overlay = document.getElementById('modalOverlay');
const modalTitle = document.getElementById('modalTitle');
const modalBody = document.getElementById('modalBody');
const modalClose = document.getElementById('modalClose');

function openModal(key) {
  const content = MODAL_CONTENT[key];
  if (!content) return;
  modalTitle.textContent = content.titulo;
  modalBody.innerHTML = content.html;
  overlay.classList.add('open');
  document.body.classList.add('modal-open');
}

function closeModal() {
  overlay.classList.remove('open');
  document.body.classList.remove('modal-open');
}

document.querySelectorAll('[data-modal]').forEach(link => {
  link.addEventListener('click', (e) => {
    e.preventDefault();
    openModal(link.dataset.modal);
  });
});

modalClose.addEventListener('click', closeModal);

overlay.addEventListener('click', (e) => {
  if (e.target === overlay) closeModal();
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeModal();
});