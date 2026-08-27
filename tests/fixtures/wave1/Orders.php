<?php

namespace App\Billing;

use App\Models\User;
use App\Support\Money as M;

trait Auditable
{
}

enum Status
{
    case Open;
}

class Order
{
    use Auditable;

    public function subtotal()
    {
        return M::zero();
    }

    public function tax()
    {
        return $this->subtotal();
    }
}

function load($root)
{
    User::find($root);
    return new Order();
}
