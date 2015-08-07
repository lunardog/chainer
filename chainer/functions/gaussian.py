import numpy

from chainer import cuda
from chainer import function
from chainer.utils import type_check


class Gaussian(function.Function):

    """Gaussian sampling function.

    In forward calculation, this funciton takes mean and logarithm of variance
    as inputs, and draw a sample from a gaussian distribution.
    """

    def __init__(self):
        self.eps = None

    def check_type_forward(self, in_types):
        type_check.expect(in_types.size() == 2)

        m_type, v_type = in_types
        type_check.expect(
            m_type.dtype == numpy.float32,
            v_type.dtype == numpy.float32,
            m_type.shape == v_type.shape,
        )

    def check_type_backward(self, in_types, out_types):
        type_check.expect(out_types.size() == 1)
        m_type, v_type = in_types
        g_type, = out_types

        type_check.expect(
            g_type.dtype == numpy.float32,
            g_type.shape == m_type.shape,
        )

    def forward_cpu(self, inputs):
        mean, ln_var = inputs
        if self.eps is None:
            self.eps = numpy.random.standard_normal(ln_var.shape) \
                                   .astype(numpy.float32)

        self.noise = numpy.exp(ln_var * 0.5) * self.eps
        return mean + self.noise,

    def forward_gpu(self, inputs):
        cupy = cuda.cupy
        mean, ln_var = inputs
        if self.eps is None:
            self.eps = cupy.random.standard_normal(
                ln_var.shape, dtype=mean.dtype)

        self.noise = cupy.empty_like(mean)
        cuda.elementwise(
            ['noise', 'v', 'e'],
            'noise[i] = exp(v[i] / 2) * e[i]',
            'gaussian_forward'
        )(self.noise, ln_var, self.eps)
        return mean + self.noise,

    def backward(self, inputs, grad_output):
        g, = grad_output
        return g, g * self.noise * g.dtype.type(0.5),


def gaussian(mean, ln_var):
    """Gaussian sampling function.

    It takes mean :math:`\\mu` and logarithm of variance
    :math:`\\log(\\sigma^2)` as input and output a sample drawn from gaussian
    :math:`N(\\mu, \\sigma)`.

    Args:
        mean (~chainer.Variable): Input variable representing mean
            :math:`\\mu`.
        ln_var (~chainer.Variable): Input variable representing logarithm of
            variance :math:`\\log(\\sigma^2)`.

    Returns:
        ~chainer.Variable: Output variable.

    """
    return Gaussian()(mean, ln_var)
