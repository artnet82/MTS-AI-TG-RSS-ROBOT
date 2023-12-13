// JavaScript-код для обновления содержимого страницы
<script>
  function updatePageWithNewFile(fileUrl) {
    // Очистка содержимого страницы
    document.getElementById('content').innerHTML = '';

    // Создание нового элемента <iframe> для загрузки файла
    var iframe = document.createElement('iframe');
    iframe.src = fileUrl;
    iframe.style.display = 'none';

    // Обработка события загрузки файла
    iframe.onload = function() {
      // Когда файл загружен, обновляем содержимое страницы
      document.getElementById('content').innerHTML = iframe.contentDocument.body.innerHTML;
    };

    // Добавление <iframe> на страницу
    document.body.appendChild(iframe);
  }

  // Пример использования функции updatePageWithNewFile
  var fileUrl = 'новый_файл.html';
  updatePageWithNewFile(fileUrl);
</script>
