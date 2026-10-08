<?php

declare(strict_types=1);

return [
    'history' => ['encrypt' => true],
    'ssr' => ['enabled' => false],
    'pages' => [
        'ensure_pages_exist' => true,
        'paths' => [resource_path('js/pages')],
        'extensions' => ['vue'],
    ],
    'testing' => ['ensure_pages_exist' => true],
    'devtools' => ['enabled' => false],
];
