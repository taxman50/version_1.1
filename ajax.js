function nameCheck(username)
{

    if (username =="")
        return;

    var ajax = new XMLHttpRequest();

    ajax.onreadystatechange = function(){
        if (ajax.readyState == 4 && ajax.status == 200){
            $('#username').html(ajax.responseText);
        }
};

ajax.open('GET','/check', true);
ajax.send();
}