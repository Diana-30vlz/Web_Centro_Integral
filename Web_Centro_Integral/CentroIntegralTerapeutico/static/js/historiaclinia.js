// static/js/historia_clinica.js

document.addEventListener('DOMContentLoaded', function() {
    console.log('Script de Historia Clínica cargado.');

    // --- Funcionalidad 1: Mostrar/Ocultar campos condicionalmente ---
    // Esta función hace que un campo (o su contenedor) aparezca/desaparezca
    // basándose en la selección de un checkbox o un grupo de radio buttons.
    //
    // Parámetros:
    // - triggerSelector: Selector CSS para el checkbox o los radio buttons que activan la condición.
    //                    Ej: '#id_tiene_alergias' (para checkbox) o 'input[name="grupo_radio_alergias"]' (para radios)
    // - targetFieldId: ID del campo HTML que debe mostrarse/ocultarse.
    //                    Ej: 'id_descripcion_alergias'
    // - conditionValue: El valor que debe tener el 'trigger' para que el 'targetField' se muestre.
    //                    - Para checkboxes: 'true' (si debe mostrarse cuando está marcado) o 'false' (cuando no está marcado).
    //                    - Para radio buttons: El valor del radio button (ej. 'Si', 'True', '1') que activa la muestra.
    // - parentSelectorToHide: Selector CSS para el elemento padre que quieres ocultar/mostrar (por defecto es el div más cercano).
    //                         Puedes usar '.mb-3', '.form-group', etc., dependiendo de la estructura de tu HTML.

    function setupConditionalField(triggerSelector, targetFieldId, conditionValue, parentSelectorToHide = '.mb-3, .row, div') {
        const triggers = document.querySelectorAll(triggerSelector);
        const targetFieldElement = document.getElementById(targetFieldId);

        if (!targetFieldElement) {
            console.warn(`[JS Condicional] Campo dependiente no encontrado: #${targetFieldId}.`);
            return;
        }

        // Encontrar el contenedor más cercano del campo objetivo para ocultarlo/mostrarlo
        const targetContainer = targetFieldElement.closest(parentSelectorToHide);
        if (!targetContainer) {
            console.warn(`[JS Condicional] Contenedor para el campo #${targetFieldId} no encontrado usando selector: ${parentSelectorToHide}.`);
            return;
        }

        const updateVisibility = () => {
            let isConditionMet = false;

            if (triggers.length === 0) {
                 // No triggers found, assume default visibility based on conditionValue
                 isConditionMet = conditionValue; // If boolean, use it directly
            } else if (triggers[0].type === 'checkbox') {
                // Si es un checkbox, la condición es que esté marcado (o no, según conditionValue)
                isConditionMet = triggers[0].checked === conditionValue;
            } else if (triggers[0].type === 'radio') {
                // Si son radio buttons, verificamos el valor del radio seleccionado
                for (const radio of triggers) {
                    if (radio.checked && radio.value === conditionValue) {
                        isConditionMet = true;
                        break;
                    }
                }
            }

            if (isConditionMet) {
                targetContainer.style.display = 'block'; // Mostrar el contenedor
                // Opcional: Si el campo debe ser requerido cuando está visible
                // targetFieldElement.setAttribute('required', 'required');
            } else {
                targetContainer.style.display = 'none'; // Ocultar el contenedor
                // Opcional: Limpiar el valor y quitar el "required" cuando está oculto
                // targetFieldElement.removeAttribute('required');
                // targetFieldElement.value = '';
            }
        };

        // Añadir listeners para detectar cambios en los triggers
        triggers.forEach(trigger => {
            trigger.addEventListener('change', updateVisibility);
        });

        // Ejecutar al cargar la página para establecer el estado inicial
        updateVisibility();
    }


    // --- EJEMPLOS DE USO para tu Historia Clínica ---
    // Para usar esta función, necesitas saber los IDs de tus campos HTML.
    // Django los genera usando 'id_<nombre_campo_del_modelo>'.

    // Ejemplo 1: Campo "Alergias - Sí/No" y un campo de texto "Descripción de alergias"
    // Asumiendo que en tu models.py tienes:
    // tiene_alergias = models.BooleanField(default=False) // O ChoiceField con 'Si'/'No'
    // descripcion_alergias = models.TextField(blank=True, null=True)
    //
    // Si 'tiene_alergias' es un BooleanField (checkbox):
    // setupConditionalField('#id_tiene_alergias', 'id_descripcion_alergias', true);
    //
    // Si 'tiene_alergias' es un ChoiceField con radio buttons de valor 'Si'/'No':
    // setupConditionalField('input[name="tiene_alergias"]', 'id_descripcion_alergias', 'Si'); // O 'True' si el valor es booleano

    // --- IMPORTANTE: Reemplaza estos ejemplos con los IDs y valores reales de tus campos ---

    // Ejemplo para 'Producto a la vista' del consentimiento que es BooleanField:
    // setupConditionalField('#id_producto_a_vista_si_no', 'id_reaccion_tiempo', true);
    //
    // Para cualquier otro BooleanField 'si/no' donde 'si' muestra algo:
    // setupConditionalField('#id_nombre_del_campo_boolean', 'id_nombre_del_campo_dependiente', true);

    // Si tuvieras un campo de tipo ChoiceField con opciones 'Si'/'No' (usando radios):
    // setupConditionalField('input[name="nombre_del_campo_choice"]', 'id_nombre_del_campo_dependiente', 'Si');


    // --- Funcionalidad 2: Integración de un Date Picker (Selector de Fecha) ---
    // Para que tus campos de fecha se vean profesionales con un calendario interactivo,
    // la mejor opción es usar una librería JavaScript de date picker.
    // Una opción popular y ligera es Flatpickr: https://flatpickr.js.org/
    //
    // Pasos para usar Flatpickr (o similar):
    // 1. **Cargar la librería:**
    //    Añade el CSS y JS de Flatpickr en tu plantilla base o en la plantilla de tu formulario.
    //    Ejemplo en tu `Base.html` o en `historia_clinica_form.html` (dentro de {% block extra_head %}/extra_body %}:
    //    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css">
    //    <script src="https://cdn.jsdelivr.net/npm/flatpickr"></script>
    // 2. **Inicializarlo en tu JS:**
    //    En `historia_clinica.js`, después de cargar Flatpickr:
    /*
    const dateInput = document.getElementById('id_fecha'); // Reemplaza 'id_fecha' con el ID de tu campo de fecha
    if (dateInput) {
        flatpickr(dateInput, {
            dateFormat: "Y-m-d", // Formato de fecha (ej. "AAAA-MM-DD")
            locale: "es",        // Idioma (si has cargado el locale de Flatpickr)
            // Otras opciones: enableTime: true, noCalendar: true, etc.
        });
    }
    // Repite para cualquier otro campo de fecha que tengas
    const fechaNacimientoInput = document.getElementById('id_fecha_nacimiento');
    if (fechaNacimientoInput) {
        flatpickr(fechaNacimientoInput, {
            dateFormat: "Y-m-d",
            locale: "es",
        });
    }
    */

    // --- Otros efectos visuales "profesionales" ---
    // Muchos efectos de "profesionalismo" como resaltar campos al enfocar,
    // transiciones suaves, etc., ya son manejados muy bien por frameworks CSS
    // como Bootstrap, que ya estás utilizando. La clave es un diseño limpio y funcional.

});