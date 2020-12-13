const TIME_TO_TWEEN = 200; //ms

var QR_DEBOUNCE = true
function QRToggle (targetOpacity)
{
    if (QR_DEBOUNCE)
    {
        QR_DEBOUNCE = false; 
        var overlay = document.getElementsByClassName("overlayed")[0];
        overlay.style.display = "block";
        var opacity = {op: 1 - targetOpacity};
    
        function update()
        {
            overlay.style.opacity = opacity.op;
        }

        function end()
        {
            if (targetOpacity == 0)
            {
                overlay.style.display = "none";
            }
        }
    
        new TWEEN.Tween(opacity)
            .to({op: targetOpacity}, TIME_TO_TWEEN)
            .onUpdate(update)
            .onComplete(end)
            .start();
    
        animate()
        QR_DEBOUNCE = true;
    }
}

function animate(time) {
    var id = requestAnimationFrame(animate);
    var result = TWEEN.update(time);

    if (!result) { cancelAnimationFrame(id); }
}